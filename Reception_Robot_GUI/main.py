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
from MQTT.publisher_angle import AnglePublisher
from MQTT.mqtt_publisher_config import get_topic

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        apply_custom_fonts(self.ui)

        # Khởi tạo label hiển thị góc lệch
        if hasattr(self.ui, 'label_deviation_angle_2'):
            self.ui.label_deviation_angle_2.setText("Góc lệch (Home→wp15): --°")

        # ===== AUTO RETURN =====
        self.auto_return_timer = QTimer()
        self.auto_return_timer.setSingleShot(True)
        self.auto_return_timer.timeout.connect(self.auto_return_home)

        self.last_goal = None
        self.HOME_NAME = "Home"   

        # Danh sách người dùng
        self.registered_users = [
            {"username": "hoaiphu", "password": "123", "fullname": "Admin User", "phone": "0123456789", "verify": "fablab"},
            {"username": "bthw", "password": "123", "fullname": "User", "phone": "0987654321", "verify": "fablab"}
        ]

        # ===== KHỞI TẠO MANAGERS =====
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

        # ===== UI NAVIGATION =====
        self.ui.stackedWidget.setCurrentWidget(self.ui.login)
        self.ui.Page.setCurrentWidget(self.ui.Page_signin)

        # Kết nối sự kiện
        self._connect_signals()

    def _connect_signals(self):
        self.ui.Signin_btn_signup.clicked.connect(lambda: self.ui.Page.setCurrentWidget(self.ui.Page_signup))
        self.ui.Signin_btn_signin.clicked.connect(lambda: self.ui.Page.setCurrentWidget(self.ui.Page_signin))
        self.ui.Signin_btn_login.clicked.connect(self._handle_login)
        self.ui.Signup_btn_signup.clicked.connect(self._handle_signup)
        
        self.ui.comboBox_2.currentTextChanged.connect(self.handle_page_switch)
        self.ui.logout.clicked.connect(self._handle_logout)
        self.ui.logout_2.clicked.connect(self._handle_logout)
        self.ui.mode_select_2.currentTextChanged.connect(self.handle_mode_switch)

    # ================= LOGIN =================
    def _handle_login(self):
        success = handle_login(self.ui, self.registered_users, main_window=self)
        if success:
            self.ui.stackedWidget.setCurrentWidget(self.ui.robot)
            self.ui.stackedWidget_2.setCurrentWidget(self.ui.page_control_2)

            self.admin_camera_tab = CameraTab(self.ui.camera_2, self.shared_browser)
            self.admin_location_tab = LocationTab(self.ui.view_map_2)
            self.admin_location_tab.logger.cte_signal.connect(self.telemetry_tab.update_cte)

            self.arrival_manager.subscriber_thread.arrival_update.connect(self.handle_arrival_signal)

            self.location_manager = LocationManager(self.ui)
            self.location_manager.location_tab = self.admin_location_tab
            self.location_manager.start_location_subscriber()

            self.goal_manager = GoalManager(self.ui)
            self.goal_manager.location_tab = self.admin_location_tab
            self.goal_manager.start_goal_subscriber()

            self.add_path_planning_buttons(self.admin_location_tab)

    def _handle_signup(self):
        if handle_signup(self.ui, self.registered_users, main_window=self):
            self.ui.stackedWidget.setCurrentWidget(self.ui.login)

    def _handle_logout(self):
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle("Confirm Logout")
        msgbox.setText("Are you sure you want to log out?")
        msgbox.setIcon(QMessageBox.Icon.Question)
        msgbox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msgbox.setStyleSheet(QMSGBOX_STYLE)

        if msgbox.exec() == QMessageBox.StandardButton.Yes:
            self._shutdown_all_services()
            self.ui.stackedWidget.setCurrentWidget(self.ui.login)

    # ================= GOAL & ROTATION LOGIC =================
    def add_path_planning_buttons(self, location_tab):
        goals = location_tab.get_goal_names()
        buttons = [self.ui.btn_goal_A, self.ui.btn_goal_B, self.ui.btn_goal_C, 
                   self.ui.btn_goal_D, self.ui.btn_goal_E, self.ui.btn_goal_F,
                   self.ui.btn_goal_G, self.ui.btn_goal_H, self.ui.btn_goal_I]

        for btn, name in zip(buttons, goals):
            btn.setText(name)
            btn.clicked.connect(lambda checked=False, n=name: self.send_goal(n))

    def send_goal(self, place: str):
        """Logic gửi mục tiêu và TỰ ĐỘNG XOAY so góc lệch khi bắt đầu di chuyển"""
        print(f"[ACTION] Sending goal: {place}")
        
        # 1. Gọi LocationTab tính toán đường đi (Hàm plan_path sẽ gửi lệnh xoay MQTT bên trong)
        if hasattr(self, 'admin_location_tab'):
            # Gọi hàm tính toán để so góc lệch hiện tại robot với điểm đầu của hành trình mới
            self.admin_location_tab.plan_path(place)

        # 2. Gửi lệnh di chuyển qua MQTT
        GoalPublisher().publish_goal(json.dumps(place))

        # 3. Quản lý Auto Return
        self.last_goal = place
        self.auto_return_timer.stop()

    def handle_arrival_signal(self, arrived):
        """Xử lý khi robot đến đích: Dừng log và Xoay hiệu chỉnh nếu về Home"""
        if arrived == 1 and hasattr(self, 'admin_location_tab'):
            self.ui.robot_mode_2.setCurrentWidget(self.ui.page_6)
            self.admin_location_tab.logger.stop_logging()
            self.ui.robot_status.setText("Idle")
            self.ui.robot_status_2.setText("Idle")

            # Xử lý xoay hiệu chỉnh khi về Home
            if self.last_goal == self.HOME_NAME:
                self._handle_home_arrival_rotation()
            else:
                # Nếu ở điểm khác, bắt đầu đếm ngược quay về Home
                print("⏱ Start 10s auto return timer")
                self.auto_return_timer.start(10000)

    def _handle_home_arrival_rotation(self):
        """Tính toán góc lệch so với trục chuẩn Home->wp15 khi robot vừa về đến Home"""
        try:
            planner = self.admin_location_tab.planner
            if 'wp15' in planner.waypoints and 'Home' in planner.all_nodes:
                home_pt = np.array(planner.all_nodes['Home'], dtype=float)
                wp15_pt = np.array(planner.waypoints['wp15'], dtype=float)

                # Lấy hướng robot hiện tại
                theta_now = float(self.admin_location_tab.last_position[2])
                heading_deg = float(self.admin_location_tab._theta_to_scene_deg(theta_now))

                heading_rad = np.deg2rad(heading_deg)
                heading_vec = np.array([np.cos(heading_rad), np.sin(heading_rad)], dtype=float)
                prev_pt = home_pt - heading_vec * 80.0

                angle_deg, sign, _ = planner._compute_angle_between(prev_pt, home_pt, wp15_pt)
                normalized_angle = int((sign * angle_deg + 360.0) % 360.0)

                # Cập nhật UI
                if hasattr(self.ui, 'label_deviation_angle_2'):
                    self.ui.label_deviation_angle_2.setText(f"Xoay (Home→wp15): {normalized_angle}°")

                # Gửi lệnh xoay MQTT
                def _publish():
                    pub = AnglePublisher()
                    try: pub.topic = get_topic("xoay")
                    except: pass
                    pub.publish_angle(normalized_angle)

                QTimer.singleShot(0, _publish)
                QTimer.singleShot(5000, _publish)
        except Exception as e:
            print(f"Error arrival rotation: {e}")

    # ================= AUTO RETURN =================
    def auto_return_home(self):
        if self.last_goal != self.HOME_NAME:
            self.send_goal(self.HOME_NAME)

    # ================= HỆ THỐNG =================
    def handle_page_switch(self, text):
        mapping = {"Control Panel": self.ui.page_control_2, "Attendance": self.ui.page_attendance_2, "Robot Telemetry": self.ui.page_data}
        if text in mapping: self.ui.stackedWidget_2.setCurrentWidget(mapping[text])

    def handle_mode_switch(self, text):
        if text == "Manual": self.ui.robot_mode_2.setCurrentWidget(self.ui.page_5)
        elif text == "Auto": self.ui.robot_mode_2.setCurrentWidget(self.ui.page_6)

    def _shutdown_all_services(self):
        # Dừng các manager một cách an toàn
        managers = [self.battery_manager, self.attendance_manager, self.velocity_manager, 
                    self.arrival_manager, self.telemetry_manager]
        if hasattr(self, 'location_manager'): managers.append(self.location_manager)
        if hasattr(self, 'goal_manager'): managers.append(self.goal_manager)
        
        for m in managers:
            for attr in dir(m):
                if attr.startswith("stop_"):
                    getattr(m, attr)()

    def closeEvent(self, event):
        self._shutdown_all_services()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.showMaximized()
    sys.exit(app.exec())