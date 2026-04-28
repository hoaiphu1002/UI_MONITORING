import os, sys, json
import numpy as np
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox
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

        # ===== AUTO RETURN =====
        self.auto_return_timer = QTimer()
        self.auto_return_timer.setSingleShot(True)
        self.auto_return_timer.timeout.connect(self.auto_return_home)

        self.last_goal = None
        self.HOME_NAME = "Home"   

        # list user
        self.registered_users = [
            {
            "username": "hoaiphu",
            "password": "123",
            "fullname": "Admin User",
            "phone": "0123456789",
            "verify": "fablab"
        },
        {
            "username": "bthw",
            "password": "123",
            "fullname": "Admin User",
            "phone": "0987654321",
            "verify": "fablab"
        }]

        # ===== STATUS =====
        self.battery_manager = BatteryManager(self.ui)
        self.battery_manager.start_battery_subscriber()

        # ===== CONTROL =====
        self.camera_controller = CameraController()
        self.shared_browser = self.camera_controller.get_browser()

        self.velocity_manager = VelocityManager(self.ui)
        self.velocity_manager.start_velocity_subscriber()

        self.arrival_manager = ArrivalManager(self.ui)
        self.arrival_manager.start_arrival_subscriber()

        self.ui.mode_select_2.currentTextChanged.connect(self.handle_mode_switch)

        # ===== ATTENDANCE =====
        self.attendance_tab = AttendanceTab(self.ui)
        self.attendance_manager = AttendanceManager(self.ui, self.attendance_tab)
        self.attendance_manager.start_attendance_subscriber()

        # ===== TELEMETRY =====
        self.telemetry_tab = PlotTelemetry(self.ui)
        self.telemetry_manager = TelemetryManager(self.ui, self.telemetry_tab)
        self.telemetry_manager.start_telemetry_subscriber()

        # ===== INIT UI =====
        self.ui.stackedWidget.setCurrentWidget(self.ui.login)
        self.ui.Page.setCurrentWidget(self.ui.Page_signin)
        self.ui.Dashboard.setCurrentWidget(self.ui.Dashboard_signin)

        # ===== LOGIN EVENTS =====
        self.ui.Signin_btn_signup.clicked.connect(lambda: self.ui.Page.setCurrentWidget(self.ui.Page_signup))
        self.ui.Signin_btn_signin.clicked.connect(lambda: self.ui.Page.setCurrentWidget(self.ui.Page_signin))
        self.ui.Signin_btn_guest.clicked.connect(self._handle_guest)
        self.ui.Signin_btn_login.clicked.connect(self._handle_login)
        self.ui.Signup_btn_signup.clicked.connect(self._handle_signup)

        # ===== AFTER LOGIN =====
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

            self.add_path_planning_buttons(self.admin_location_tab)

            self.arrival_manager.subscriber_thread.arrival_update.connect(
                lambda arrived: self.handle_arrival_signal(arrived)
            )

            self.location_manager = LocationManager(self.ui)
            self.location_manager.location_tab = self.admin_location_tab
            self.location_manager.start_location_subscriber()

            self.goal_manager = GoalManager(self.ui)
            self.goal_manager.location_tab = self.admin_location_tab
            self.goal_manager.start_goal_subscriber()

    def _handle_signup(self):
        success = handle_signup(self.ui, self.registered_users, main_window=self)
        if success:
            self.ui.stackedWidget.setCurrentWidget(self.ui.login)

    def _handle_guest(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.guest)

        self.guest_camera_tab = CameraTab(self.ui.camera_4, self.shared_browser)
        self.guest_location_tab = LocationTab(self.ui.view_map)

        self.add_path_planning_buttons(self.guest_location_tab)

        self.location_manager = LocationManager(self.ui)
        self.location_manager.location_tab = self.guest_location_tab
        self.location_manager.start_location_subscriber()

    # ================= LOGOUT =================
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

    # ================= UI =================
    def handle_page_switch(self, text):
        if text == "Control Panel":
            self.ui.stackedWidget_2.setCurrentWidget(self.ui.page_control_2)
        elif text == "Attendance":
            self.ui.stackedWidget_2.setCurrentWidget(self.ui.page_attendance_2)
        elif text == "Robot Telemetry":
            self.ui.stackedWidget_2.setCurrentWidget(self.ui.page_data)

    def handle_mode_switch(self, text):
        if text == "Manual":
            self.ui.robot_mode_2.setCurrentWidget(self.ui.page_5)
        elif text == "Auto":
            self.ui.robot_mode_2.setCurrentWidget(self.ui.page_6)

    # ================= BUTTON =================
    def add_path_planning_buttons(self, location_tab):
        goals = location_tab.get_goal_names()
        buttons = [
            self.ui.btn_goal_A,
            self.ui.btn_goal_B,
            self.ui.btn_goal_C,
            self.ui.btn_goal_D,
            self.ui.btn_goal_E,
            self.ui.btn_goal_F
        ]

        for btn, name in zip(buttons, goals):
            btn.setText(name)
            btn.clicked.connect(lambda checked=False, n=name: self.send_goal(n))

    # ================= GOAL =================
    def send_goal(self, place: str):
        goal_json = json.dumps(place)
        print(f"Goal: {goal_json}")

        publisher = GoalPublisher()
        publisher.publish_goal(goal_json)

        # ===== AUTO RETURN =====
        self.last_goal = place
        self.auto_return_timer.stop()  # reset timer

    # ================= ARRIVAL =================
    def handle_arrival_signal(self, arrived):
        print(f"[DEBUG] handle_arrival_signal called with arrived={arrived}")
        if hasattr(self, 'admin_location_tab'):
            self.ui.robot_mode_2.setCurrentWidget(self.ui.page_6)
            self.admin_location_tab.logger.stop_logging()
            self.ui.robot_status.setText("Idle")
            self.ui.robot_status_2.setText("Idle")

            # ===== START TIMER =====
            if self.last_goal != self.HOME_NAME:
                print("⏱ Start 10s auto return timer")
                self.auto_return_timer.start(10000) # CHỈNH THỜI GIAN CHỜ 


            # SỬA: Tính góc giữa hướng robot và waypoint liền kề (không chỉ điểm đầu/cuối)
            try:
                # Lấy danh sách waypoint chi tiết (bao gồm cả trung gian)
                waypoints = getattr(self.admin_location_tab, 'full_plan_points', None)
                print(f"[DEBUG] full_plan_points: {waypoints}")
                if waypoints is not None and len(waypoints) >= 2:
                    # Lấy vị trí hiện tại của robot
                    curx, cury, _ = self.admin_location_tab.last_position
                    print(f"[DEBUG] Robot position: x={curx}, y={cury}")
                    # Tìm waypoint gần nhất với vị trí hiện tại
                    dists = [np.hypot(curx - wp['x'], cury - wp['y']) for wp in waypoints]
                    idx = int(np.argmin(dists))
                    print(f"[DEBUG] Closest waypoint index: {idx}, point: {waypoints[idx]}")
                    # Lấy waypoint liền kề tiếp theo (nếu có)
                    if idx + 1 < len(waypoints):
                        wp_next = waypoints[idx + 1]
                        print(f"[DEBUG] Next waypoint: {wp_next}")
                        # Vector từ robot đến waypoint tiếp theo
                        vec_next = np.array([wp_next['x'] - curx, wp_next['y'] - cury], dtype=float)
                        norm = np.linalg.norm(vec_next) + 1e-8
                        vec_next_norm = vec_next / norm

                        # Hướng hiện tại của robot
                        heading_deg = getattr(self.admin_location_tab, '_display_heading_deg', None)
                        if heading_deg is None:
                            theta_now = float(self.admin_location_tab.last_position[2])
                            heading_deg = float(self.admin_location_tab._theta_to_scene_deg(theta_now))
                        print(f"[DEBUG] heading_deg: {heading_deg}")
                        heading_rad = np.deg2rad(float(heading_deg))
                        heading_vec = np.array([np.cos(heading_rad), np.sin(heading_rad)], dtype=float)

                        # Tính góc giữa hướng robot và hướng waypoint tiếp theo
                        dot = np.clip(np.dot(heading_vec, vec_next_norm), -1.0, 1.0)
                        angle = np.arccos(dot) * 180.0 / np.pi
                        cross = np.cross(heading_vec, vec_next_norm)
                        sign = np.sign(cross)
                        signed_angle = angle * sign
                        print(f"[ARRIVAL] heading_vec: {heading_vec}")
                        print(f"[ARRIVAL] vec_next_norm: {vec_next_norm}")
                        print(f"[ARRIVAL] dot (tích vô hướng): {dot}")
                        print(f"[ARRIVAL] angle (arccos(dot)): {angle:.2f}°")
                        print(f"[ARRIVAL] cross (tích có hướng): {cross}")
                        print(f"[ARRIVAL] sign: {sign}")
                        print(f"[ARRIVAL] signed_angle: {signed_angle:.2f}°")
                        angle_to_publish = int((signed_angle + 360.0) % 360.0)
                        print(f"[ARRIVAL] angle_to_publish (0-359): {angle_to_publish}°")
                        print(f"[ARRIVAL] Góc giữa hướng robot và hướng đến waypoint tiếp theo: {signed_angle:.1f}° (abs={abs(signed_angle):.1f}°)")

                        # Luôn gửi lệnh xoay, không kiểm tra ANGLE_THRESHOLD
                        def _publish_xoay_angle():
                            pub = AnglePublisher()
                            try:
                                pub.topic = get_topic("xoay")
                            except Exception:
                                pass
                            pub.publish_angle(angle_to_publish)
                        QTimer.singleShot(0, _publish_xoay_angle)
                        print(f"[ARRIVAL] Publish xoay: {angle_to_publish}° (0-359, chiều ngắn nhất) để hướng về waypoint tiếp theo")
                        return
            except Exception as e:
                print(f"[ARRIVAL] Angle to next waypoint failed: {e}")

            # Nếu về Home thì vẫn giữ logic cũ
            if self.last_goal == self.HOME_NAME:
                try:
                    planner = self.admin_location_tab.planner
                    if 'wp14' in planner.waypoints and 'Home' in planner.all_nodes:
                        home_pt = np.array(planner.all_nodes['Home'], dtype=float)
                        wp14_pt = np.array(planner.waypoints['wp14'], dtype=float)

                        heading_deg = getattr(self.admin_location_tab, '_display_heading_deg', None)
                        if heading_deg is None:
                            theta_now = float(self.admin_location_tab.last_position[2])
                            heading_deg = float(self.admin_location_tab._theta_to_scene_deg(theta_now))

                        heading_rad = np.deg2rad(float(heading_deg))
                        heading_vec = np.array([np.cos(heading_rad), np.sin(heading_rad)], dtype=float)
                        prev_pt = home_pt - heading_vec * 80.0

                        angle_deg, sign, dot = planner._compute_angle_between(prev_pt, home_pt, wp14_pt)
                        planner.last_deviation_angle = angle_deg
                        planner.last_deviation_sign = sign
                        planner.last_deviation_signed_angle = sign * angle_deg
                        planner.last_deviation_angle_360 = (planner.last_deviation_signed_angle + 360.0) % 360.0
                        planner.last_deviation_dot = dot
                        planner._draw_angle_visual(prev_pt, home_pt, wp14_pt, angle_deg, sign)

                        normalized_angle = int(planner.last_deviation_angle_360)
                        def _publish_xoay_angle():
                            pub = AnglePublisher()
                            try:
                                pub.topic = get_topic("xoay")
                            except Exception:
                                pass
                            pub.publish_angle(normalized_angle)

                        QTimer.singleShot(0, _publish_xoay_angle)
                        QTimer.singleShot(5000, _publish_xoay_angle)

                        print(
                            f"[ARRIVAL] Heading deviation at Home: "
                            f"signed={planner.last_deviation_signed_angle:.1f}°, "
                            f"angle_360={planner.last_deviation_angle_360:.1f}°, "
                            f"publish_times=2, interval_ms=5000, value={normalized_angle}"
                        )
                except Exception as e:
                    print(f"[MQTT ANGLE] Compute/publish on arrival failed: {e}")

    # ================= AUTO RETURN =================
    def auto_return_home(self):
        print("⚠️ Auto return HOME")

        if self.last_goal == self.HOME_NAME:
            return

        self.send_goal(self.HOME_NAME)

    # ================= SHUTDOWN =================
    def _shutdown_all_services(self):
        self.battery_manager.stop_battery_subscriber()
        self.attendance_manager.stop_attendance_subscriber()
        self.location_manager.stop_location_subscriber()
        self.velocity_manager.stop_velocity_subscriber()
        self.arrival_manager.stop_arrival_subscriber()
        self.telemetry_manager.stop_telemetry_subscriber()
        self.goal_manager.stop_goal_subscriber()

    def closeEvent(self, event):
        print("Closinggg...")
        self._shutdown_all_services()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.showMaximized()
    sys.exit(app.exec())