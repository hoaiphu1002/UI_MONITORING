import os, sys, json
import numpy as np
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QTimer   

from ui.font_configurator import apply_custom_fonts
from ui.style import QMSGBOX_STYLE
from ui.main_ui import Ui_MainWindow
from user import handle_login, handle_signup
from attendance import AttendanceTab

from manager.manager_attendance import AttendanceManager
from manager.manager_battery import BatteryManager
from manager.manager_location import LocationManager 
from manager.manager_arrival import ArrivalManager 
from manager.manager_velocity import VelocityManager 
from manager.manager_telemetry import TelemetryManager
from manager.manager_goal import GoalManager

from location import LocationTab
from camera import CameraController, CameraTab
from robot_telemetry import PlotTelemetry
from MQTT.publisher_goal import GoalPublisher 

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        apply_custom_fonts(self.ui)

        # Cấu hình auto return
        self.auto_return_timer = QTimer()
        self.auto_return_timer.setSingleShot(True)
        self.auto_return_timer.timeout.connect(self.auto_return_home)
        self.last_goal = None
        self.HOME_NAME = "Home"

        # Danh sách user cũ của bạn
        self.registered_users = [
            {"username": "hoaiphu", "password": "123", "fullname": "Admin", "verify": "fablab"},
            {"username": "bthw", "password": "123", "fullname": "User", "verify": "fablab"}
        ]

        # Khởi tạo các Manager
        self.battery_manager = BatteryManager(self.ui)
        self.battery_manager.start_battery_subscriber()
        self.camera_controller = CameraController()
        self.shared_browser = self.camera_controller.get_browser()
        self.velocity_manager = VelocityManager(self.ui)
        self.velocity_manager.start_velocity_subscriber()
        self.arrival_manager = ArrivalManager(self.ui)
        self.arrival_manager.start_arrival_subscriber()
        self.attendance_tab = AttendanceTab(self.ui)
        self.attendance_manager = AttendanceManager(self.ui, self.attendance_tab)
        self.attendance_manager.start_attendance_subscriber()
        self.telemetry_tab = PlotTelemetry(self.ui)
        self.telemetry_manager = TelemetryManager(self.ui, self.telemetry_tab)
        self.telemetry_manager.start_telemetry_subscriber()

        # GIỮ NGUYÊN CẤU TRÚC LOGIN/SIGNUP CỦA BẠN
        self.ui.stackedWidget.setCurrentWidget(self.ui.login)
        self.ui.Page.setCurrentWidget(self.ui.Page_signin)

        self.ui.Signin_btn_signup.clicked.connect(lambda: self.ui.Page.setCurrentWidget(self.ui.Page_signup))
        self.ui.Signin_btn_signin.clicked.connect(lambda: self.ui.Page.setCurrentWidget(self.ui.Page_signin))
        self.ui.Signin_btn_login.clicked.connect(self._handle_login)
        self.ui.Signup_btn_signup.clicked.connect(self._handle_signup)
        self.ui.logout.clicked.connect(self._handle_logout)
        self.ui.logout_2.clicked.connect(self._handle_logout)
        
        self.ui.comboBox_2.currentTextChanged.connect(self.handle_page_switch)
        self.ui.mode_select_2.currentTextChanged.connect(self.handle_mode_switch)

    def _handle_login(self):
        # Vẫn dùng hàm handle_login cũ của bạn để check Username/Password
        success = handle_login(self.ui, self.registered_users, main_window=self)
        if success:
            self.ui.stackedWidget.setCurrentWidget(self.ui.robot)
            self.admin_camera_tab = CameraTab(self.ui.camera_2, self.shared_browser)
            self.admin_location_tab = LocationTab(self.ui.view_map_2)
            
            # Kết nối sự kiện đến đích
            self.arrival_manager.subscriber_thread.arrival_update.connect(self.handle_arrival_signal)

            self.location_manager = LocationManager(self.ui)
            self.location_manager.location_tab = self.admin_location_tab
            self.location_manager.start_location_subscriber()
            self.add_path_planning_buttons(self.admin_location_tab)

    def _handle_signup(self):
        handle_signup(self.ui, self.registered_users)

    def _handle_logout(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Logout")
        msg.setText("Are you sure?")
        msg.setStyleSheet(QMSGBOX_STYLE)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.ui.stackedWidget.setCurrentWidget(self.ui.login)

    def add_path_planning_buttons(self, location_tab):
        goals = location_tab.get_goal_names()
        buttons = [self.ui.btn_goal_A, self.ui.btn_goal_B, self.ui.btn_goal_C, 
                   self.ui.btn_goal_D, self.ui.btn_goal_E, self.ui.btn_goal_F]
        for btn, name in zip(buttons, goals):
            btn.setText(name)
            btn.clicked.connect(lambda checked=False, n=name: self.send_goal(n))

    def send_goal(self, place: str):
        print(f"[ACTION] Sending goal: {place}")
        # Gửi goal MQTT
        GoalPublisher().publish_goal(json.dumps(place))
        self.last_goal = place
        self.auto_return_timer.stop()

        # Gọi hàm tính đường (Bên trong location.py sẽ tự gửi lệnh xoay)
        if hasattr(self, 'admin_location_tab'):
            self.admin_location_tab.plan_path(place)

    def handle_arrival_signal(self, arrived):
        """Xử lý khi robot báo đã đến đích - CHỈ DỪNG, XOAY nếu về Home"""
        if not arrived:
            return

        print(f"[STATUS] Arrived at {self.last_goal}")
        self.ui.robot_status.setText("Idle")

        if hasattr(self, 'admin_location_tab'):
            self.admin_location_tab.logger.stop_logging()
            self.admin_location_tab.full_plan_points = []
            if self.last_goal == self.HOME_NAME:
                self.admin_location_tab.publish_home_rotation()
            else:
                self.admin_location_tab.publish_waypoint_rotation(self.last_goal)

        if self.last_goal != self.HOME_NAME:
            self.auto_return_timer.start(10000)

    def auto_return_home(self):
        if self.last_goal != self.HOME_NAME:
            self.send_goal(self.HOME_NAME)

    def handle_page_switch(self, text):
        mapping = {"Control Panel": self.ui.page_control_2, "Attendance": self.ui.page_attendance_2, "Robot Telemetry": self.ui.page_data}
        if text in mapping: self.ui.stackedWidget_2.setCurrentWidget(mapping[text])

    def handle_mode_switch(self, text):
        if text == "Manual": self.ui.robot_mode_2.setCurrentWidget(self.ui.page_5)
        else: self.ui.robot_mode_2.setCurrentWidget(self.ui.page_6)

    def closeEvent(self, event):
        # Dừng các manager khi tắt app
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.showMaximized()
    sys.exit(app.exec())