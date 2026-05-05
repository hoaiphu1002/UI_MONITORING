from PyQt6.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QGraphicsPolygonItem, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap, QPolygonF, QWheelEvent, QPainter, QBrush, QPen, QColor
from PyQt6.QtCore import QPointF, Qt, QTimer
import yaml, json
import numpy as np
import math
from datetime import datetime

from pathplanning_fixedwp import PathPlanner
from logger import PathLogger
from MQTT.publisher_waypoints import WaypointsPublisher

class MapGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.zoom_factor = 1.25

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)

class LocationTab(QWidget):
    def _compute_signed_turn_deg(self, heading_vec, target_vec):
        """Trả về góc quay signed từ heading -> target trong khoảng [-180, 180]."""
        h_norm = np.linalg.norm(heading_vec)
        t_norm = np.linalg.norm(target_vec)
        if h_norm < 1e-8 or t_norm < 1e-8:
            return 0.0

        h = heading_vec / h_norm
        t = target_vec / t_norm
        dot = float(np.clip(np.dot(h, t), -1.0, 1.0))
        cross_z = float(h[0] * t[1] - h[1] * t[0])
        return float(np.degrees(np.arctan2(cross_z, dot)))

    def _get_real_heading_world_rad(self):
        theta = float(self.last_position[2])
        if abs(theta) <= (2 * math.pi + 0.1):
            return theta
        return math.radians(theta)

    def publish_waypoint_rotation(self, goal_name):
        """Tính và gửi góc xoay về hướng waypoint tiếp theo (2 lần, 0ms và 5000ms)"""
        try:
            planner = self.planner
            goal_names = list(self.goals.keys())
            if goal_name in goal_names:
                idx = goal_names.index(goal_name)
                if idx + 1 < len(goal_names):
                    next_goal = goal_names[idx + 1]
                    if next_goal != "Home":
                        current_pos = np.array(self.goals[goal_name], dtype=float)
                        next_pos = np.array(self.goals[next_goal], dtype=float)
                        vec_next = next_pos - current_pos
                        heading_rad = self._get_real_heading_world_rad()
                        heading_vec = np.array([np.cos(heading_rad), np.sin(heading_rad)], dtype=float)
                        signed_angle = self._compute_signed_turn_deg(heading_vec, vec_next)
                        angle_to_publish = int(round((signed_angle + 360.0) % 360.0))
                        from MQTT.publisher_angle import AnglePublisher
                        from MQTT.mqtt_publisher_config import get_topic
                        def _publish_xoay_angle():
                            pub = AnglePublisher()
                            try:
                                pub.topic = get_topic("xoay")
                            except Exception:
                                pass
                            pub.publish_angle(angle_to_publish)
                        QTimer.singleShot(0, _publish_xoay_angle)
                        QTimer.singleShot(5000, _publish_xoay_angle)
                        QTimer.singleShot(8000, _publish_xoay_angle)
                        print(f"[WAYPOINT] Publish xoay: {angle_to_publish}° (0-359) để hướng về waypoint {next_goal} (2 lần)")
        except Exception as e:
            print(f"[WAYPOINT] Angle to waypoint failed: {e}")

    def publish_home_rotation(self):
        try:
            planner = self.planner
            if 'wp14' in planner.waypoints and 'Home' in planner.all_nodes:
                home_pt = np.array(planner.all_nodes['Home'], dtype=float)
                wp14_pt = np.array(planner.waypoints['wp14'], dtype=float)

                heading_rad = self._get_real_heading_world_rad()
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
                from MQTT.publisher_angle import AnglePublisher
                from MQTT.mqtt_publisher_config import get_topic
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
    def __init__(self, view):
        super().__init__()
        self.ui = view
        
        # Biến trạng thái để tránh tính toán trùng lặp trong thời gian ngắn
        self._is_planning = False 

        # Giữ nguyên phần khởi tạo giao diện của bạn
        layout = self.ui.parent().layout()
        self.ui.setParent(None)
        self.ui = MapGraphicsView()
        layout.addWidget(self.ui)

        self.map_scene = QGraphicsScene()
        self.ui.setScene(self.map_scene)

        self.logger = PathLogger()
        self.logger.location_tab = self
        self.trajectory_items = []

        self.planner = PathPlanner(self.map_scene)
        self.goals = self.planner.goals 
        
        home_coords = self.goals.get("Home", (825, 394))
        self.home_px, self.home_py = home_coords

        self.load_map("Reception_Robot_GUI/resources/Map/new_map2.pgm")
        
        init_x = self.map_origin[0] + (self.home_px * self.map_resolution)
        init_y = self.map_origin[1] + (self.map_height - self.home_py) * self.map_resolution

        self.last_position = [init_x, init_y, 0.0]
        self.create_robot()
        self.update_robot_gui()

        self.last_planned_path = []
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_robot_gui)
        self.update_timer.start(100)

    def load_map(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Cannot load map: {path}")
            return
        
        self.map_item = self.map_scene.addPixmap(pixmap)
        self.map_scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.ui.fitInView(self.map_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.map_width = pixmap.width()
        self.map_height = pixmap.height()

        yaml_path = path.replace(".pgm", ".yaml")
        try:
            with open(yaml_path, 'r') as file:
                map_config = yaml.safe_load(file)
                self.map_resolution = map_config['resolution']
                self.map_origin = (map_config['origin'][0], map_config['origin'][1])
        except Exception as e:
            self.map_resolution = 0.05
            self.map_origin = (-1.545, -12.181) 
            print(f"Error reading YAML: {e}")

    def create_robot(self):
        pixmap = QPixmap("Reception_Robot_GUI/resources/Icons/robot.png")
        pixmap = pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.robot_item = QGraphicsPixmapItem(pixmap)
        self.robot_item.setZValue(100)
        self.robot_w, self.robot_h = pixmap.width(), pixmap.height()
        self.robot_item.setTransformOriginPoint(self.robot_w / 2, self.robot_h / 2)
        self.robot_icon_forward_offset_deg = 90.0
        self.map_scene.addItem(self.robot_item)

        self.heading_line = self.map_scene.addLine(0, 0, 0, 0, QPen(QColor(255, 80, 0), 3))
        self.heading_line.setZValue(110)
        self.heading_arrow = QGraphicsPolygonItem()
        self.heading_arrow.setBrush(QBrush(QColor(255, 80, 0)))
        self.heading_arrow.setPen(QPen(Qt.GlobalColor.transparent, 0))
        self.heading_arrow.setZValue(111)
        self.map_scene.addItem(self.heading_arrow)
        self._last_px_py = None
        self._display_heading_deg = 0.0

    def update_robot_gui(self):
        x, y, theta = self.last_position
        px = (x - self.map_origin[0]) / self.map_resolution
        py = self.map_height - (y - self.map_origin[1]) / self.map_resolution

        self.robot_pos = (px, py)
        self.robot_item.setPos(px - self.robot_w/2, py - self.robot_h/2)

        # Luôn dùng theta thực tế từ pose để hiển thị và tính toán hướng xoay.
        self._display_heading_deg = self._theta_to_scene_deg(theta)
        self._update_heading_indicator(px, py, self._display_heading_deg)
        self.robot_item.setRotation(self._display_heading_deg + self.robot_icon_forward_offset_deg)
        self._last_px_py = (px, py)

    def set_location(self, x, y, theta):
        self.last_position = [x, y, theta]

    def _get_real_heading_scene_deg(self):
        return float(self._theta_to_scene_deg(float(self.last_position[2])))

    def _theta_to_scene_deg(self, theta):
        if abs(theta) <= (2 * math.pi + 0.1):
            theta_deg = math.degrees(theta)
        else:
            theta_deg = theta
        return -theta_deg

    def _update_heading_indicator(self, cx, cy, heading_deg):
        line_len = max(self.robot_w, self.robot_h) * 0.9
        rad = math.radians(heading_deg)
        tip_x = cx + line_len * math.cos(rad)
        tip_y = cy + line_len * math.sin(rad)
        self.heading_line.setLine(cx, cy, tip_x, tip_y)
        
        arrow_len, arrow_half_width = 10.0, 5.0
        base_x, base_y = tip_x - arrow_len * math.cos(rad), tip_y - arrow_len * math.sin(rad)
        left_x = base_x + arrow_half_width * math.cos(rad + math.pi / 2.0)
        left_y = base_y + arrow_half_width * math.sin(rad + math.pi / 2.0)
        right_x = base_x + arrow_half_width * math.cos(rad - math.pi / 2.0)
        right_y = base_y + arrow_half_width * math.sin(rad - math.pi / 2.0)
        self.heading_arrow.setPolygon(QPolygonF([QPointF(tip_x, tip_y), QPointF(left_x, left_y), QPointF(right_x, right_y)]))

    def plan_path(self, goal):
        # KHÓA LOGIC: Nếu đang tính toán thì thoát ra để tránh chạy 2 lần
        if self._is_planning:
            return
        self._is_planning = True

        try:
            ref_point = self.last_planned_path[-2] if len(self.last_planned_path) >= 2 else None
            self.clear_trajectory()
            self.trajectory_points = []
            self.trajectory_times = []

            px, py = self.robot_pos
            self.trajectory_points.append((px, py))
            self.trajectory_times.append(datetime.now())

            # Thực hiện tính toán đường đi
            self.planned_path = self.planner.find_path(self.robot_pos, goal, ref_point)
            print(f"[DEBUG] planned_path (pixel): {self.planned_path}")
            self.planner.draw_path(self.planned_path)
            self.last_planned_path = self.planned_path
            
            # Chuyển đổi sang mét
            self.plan_points = []
            for p_px, p_py in self.planned_path:
                x = self.map_origin[0] + p_px * self.map_resolution
                y = self.map_origin[1] + (self.map_height - p_py) * self.map_resolution
                self.plan_points.append({"x": round(x, 3), "y": round(y, 3)})

            curx, cury, _ = self.last_position
            current_wp = {"x": round(curx, 3), "y": round(cury, 3)}
            self.full_plan_points = self._dedupe_consecutive_waypoints([current_wp] + self.plan_points)
            print(f"[DEBUG] full_plan_points (m): {self.full_plan_points}")

            # Gửi dữ liệu MQTT
            self.logger.start_logging(self.full_plan_points)
            WaypointsPublisher().publish_waypoints(json.dumps(self.full_plan_points, indent=2))

            # Tạm thời bỏ logic tự động xoay khi nhấn waypoint mới
            # if len(self.full_plan_points) >= 2:
            #     self._handle_auto_rotation(curx, cury)

        finally:
            # Mở khóa sau khi hoàn tất (hoặc sau khi lỗi)
            # Dùng QTimer để reset khóa sau 500ms, đảm bảo các signal trùng lặp bị bỏ qua hoàn toàn
            QTimer.singleShot(500, self._reset_planning_lock)

    def _reset_planning_lock(self):
        self._is_planning = False

    def _handle_auto_rotation(self, curx, cury):
        try:
            wp_next = self.full_plan_points[1]
            vec_next = np.array([wp_next['x'] - curx, wp_next['y'] - cury], dtype=float)
            heading_rad = self._get_real_heading_world_rad()
            heading_vec = np.array([np.cos(heading_rad), np.sin(heading_rad)], dtype=float)
            signed_angle = self._compute_signed_turn_deg(heading_vec, vec_next)
            angle_to_publish = int(round((signed_angle + 360.0) % 360.0))

            from MQTT.publisher_angle import AnglePublisher
            from MQTT.mqtt_publisher_config import get_topic
            pub = AnglePublisher()
            try: pub.topic = get_topic("xoay")
            except: pass
            pub.publish_angle(angle_to_publish)
            print(f"[AUTO_XOAY] Publish xoay: {angle_to_publish}°")
        except Exception as e:
            print(f"Auto rotation error: {e}")

    def _dedupe_consecutive_waypoints(self, points):
        deduped = []
        last_p = None
        for p in points:
            curr = (p["x"], p["y"])
            if curr != last_p:
                deduped.append(p)
                last_p = curr
        return deduped

    def clear_trajectory(self):
        for item in self.trajectory_items: self.map_scene.removeItem(item)
        self.trajectory_items.clear()

    def update_trajectory(self):
        if len(self.trajectory_points) < 2: return
        self.clear_trajectory()
        pen = QPen(QColor(180, 0, 0), 3)
        for i in range(len(self.trajectory_points) - 1):
            p1, p2 = self.trajectory_points[i], self.trajectory_points[i+1]
            self.trajectory_items.append(self.map_scene.addLine(p1[0], p1[1], p2[0], p2[1], pen))

    def get_goal_names(self):
        return list(self.goals.keys())