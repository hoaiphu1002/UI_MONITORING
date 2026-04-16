from PyQt6.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QGraphicsPolygonItem, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap, QPolygonF, QWheelEvent, QPainter, QBrush, QPen, QColor
from PyQt6.QtCore import QPointF, Qt, QTimer
import yaml, json
import numpy as np
from datetime import datetime

from pathplanning_fixedwp import PathPlanner
from logger import PathLogger
from MQTT.publisher_waypoints import WaypointsPublisher
from MQTT.publisher_speed import SpeedPublisher

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
    def _theta_to_scene_deg(self, theta_rad):
        """Chuyển đổi góc radian sang độ cho scene (chuẩn hóa về [0, 360))"""
        deg = np.degrees(theta_rad)
        return deg % 360
    def __init__(self, view):
        super().__init__()
        self.ui = view

        # Thay thế widget bằng graphics view
        layout = self.ui.parent().layout()
        self.ui.setParent(None)
        self.ui = MapGraphicsView()
        layout.addWidget(self.ui)

        self.map_scene = QGraphicsScene()
        self.ui.setScene(self.map_scene)

        # Logger
        self.logger = PathLogger()
        self.logger.location_tab = self

        # Khởi tạo trajectory với điểm Home là điểm đầu tiên
        self.trajectory_items = []

        # Path planner
        self.planner = PathPlanner(self.map_scene)
        # self.planner.set_locations(self.goals)

        # Lấy danh sách goals trực tiếp từ planner
        self.goals = self.planner.goals 
        
        # Home cũng lấy từ dữ liệu tập trung
        home_coords = self.goals.get("Home", (825, 394))
        self.home_px, self.home_py = home_coords

        # Load map và các thiết lập khác
        self.load_map("Reception_Robot_GUI/resources/Map/B2_map.pgm")
        
        # Khởi tạo robot tại vị trí Home
        init_x = self.map_origin[0] + (self.home_px * self.map_resolution)
        init_y = self.map_origin[1] + (self.map_height - self.home_py) * self.map_resolution

        self.last_position = [init_x, init_y, 0.0]
        self.initial_heading_deg = 0.0  # Mốc góc ban đầu (0 độ)
        self.create_robot()
        self.create_heading_indicator()  # Thêm mũi tên hướng
        self.update_robot_gui()
    def create_heading_indicator(self):
        # Tạo heading indicator (mũi tên hướng)
        self.heading_pen = QPen(QColor(255, 0, 0), 3)
        self.heading_arrow_brush = QBrush(QColor(255, 0, 0))
        self.heading_line = self.map_scene.addLine(0, 0, 0, 0, self.heading_pen)
        self.heading_line.setZValue(110)
        self.heading_arrow = QGraphicsPolygonItem()
        self.heading_arrow.setBrush(self.heading_arrow_brush)
        self.heading_arrow.setPen(QPen(Qt.GlobalColor.transparent, 0))
        self.heading_arrow.setZValue(111)
        self.map_scene.addItem(self.heading_arrow)

        self.last_planned_path = []
        
        # Timer cập nhật vị trí từ MQTT (nếu có)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_robot_gui)
        self.update_timer.start(100)

    # ==========================================
    #                  MAP
    # ==========================================
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

        # Đọc file YAML đi kèm để lấy thông số tọa độ thực
        yaml_path = path.replace(".pgm", ".yaml")
        try:
            with open(yaml_path, 'r') as file:
                map_config = yaml.safe_load(file)
                self.map_resolution = map_config['resolution']
                self.map_origin = (map_config['origin'][0], map_config['origin'][1])
        except Exception as e:
            # Giá trị dự phòng nếu không đọc được file
            self.map_resolution = 0.05
            self.map_origin = (-1.545, -12.181) 
            print(f"Error reading YAML, using defaults: {e}")

    # ==========================================
    #               ROBOT GRAPHICS
    # ==========================================
    def create_robot(self):
        pixmap = QPixmap("Reception_Robot_GUI/resources/Icons/robot.png")
        pixmap = pixmap.scaled(30, 30, 
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)

        self.robot_item = QGraphicsPixmapItem(pixmap)
        self.robot_item.setZValue(100)
        self.robot_w = pixmap.width()
        self.robot_h = pixmap.height()
        self.robot_item.setTransformOriginPoint(self.robot_w / 2, self.robot_h / 2)
        self.robot_icon_forward_offset_deg = 90.0  # Nếu icon robot hướng lên trên, chỉnh lại nếu cần
        self.map_scene.addItem(self.robot_item)

    # ==========================================
    #          ROBOT REAL POSITION UPDATE
    # ==========================================
    def update_robot_gui(self):
        x, y, theta = self.last_position

        # Chuyển đổi từ Mét → Pixel để vẽ lên màn hình
        px = (x - self.map_origin[0]) / self.map_resolution
        py = self.map_height - (y - self.map_origin[1]) / self.map_resolution

        self.robot_pos = (px, py)
        self.robot_item.setPos(px - self.robot_w/2, py - self.robot_h/2)


        # --- Vẽ mũi tên hướng robot ---
        heading_deg = -theta if abs(theta) > 2 * np.pi else -np.degrees(theta)
        self._update_heading_indicator_arrow(px, py, heading_deg)
        # Quay hình robot theo hướng thực tế
        self.robot_item.setRotation(heading_deg + self.robot_icon_forward_offset_deg)
        # -----------------------------

        # Lưu vết đường đi (Trajectory)
        if hasattr(self, 'trajectory_points') and len(self.trajectory_points) > 0:
            current_point = (px, py)
            last_point = self.trajectory_points[-1]

            if np.linalg.norm(np.array(current_point) - np.array(last_point)) > 2:
                self.trajectory_points.append(current_point)
                self.trajectory_times.append(datetime.now())
                self.update_trajectory()

    def _update_heading_indicator_arrow(self, cx, cy, heading_deg):
        # Vẽ mũi tên hướng robot
        line_len = max(self.robot_w, self.robot_h) * 0.9
        arrow_len = 10.0
        arrow_half_width = 5.0
        rad = np.radians(heading_deg)

        tip_x = cx + line_len * np.cos(rad)
        tip_y = cy + line_len * np.sin(rad)
        self.heading_line.setLine(cx, cy, tip_x, tip_y)

        base_x = tip_x - arrow_len * np.cos(rad)
        base_y = tip_y - arrow_len * np.sin(rad)
        left_x = base_x + arrow_half_width * np.cos(rad + np.pi / 2.0)
        left_y = base_y + arrow_half_width * np.sin(rad + np.pi / 2.0)
        right_x = base_x + arrow_half_width * np.cos(rad - np.pi / 2.0)
        right_y = base_y + arrow_half_width * np.sin(rad - np.pi / 2.0)

        arrow_poly = QPolygonF([
            QPointF(tip_x, tip_y),
            QPointF(left_x, left_y),
            QPointF(right_x, right_y)
        ])
        self.heading_arrow.setPolygon(arrow_poly)

    def set_location(self, x, y, theta):
        """Hàm này nhận dữ liệu x, y, theta từ MQTT Manager"""
        self.last_position = [x, y, theta]

        # --- Kiểm tra và cập nhật tốc độ nếu gần điểm nguy hiểm ---
        try:
            from MQTT.publisher_speed import SpeedPublisher
            speed_publisher = SpeedPublisher()
            # Danh sách toạ độ nguy hiểm (theo mét)
            danger_points = [
                (3.94, 4.946),  # wp3
                (3.79, 9.296),  # wp4
                (3.59, 13.946), # ví dụ thêm các điểm khác nếu cần
                (7.14, 15.396), # restroom
                (3.89, 15.295839), # meeting room
                # ... thêm các điểm nguy hiểm khác nếu cần
            ]
            speed = 1.0
            print("[DEBUG] --- Danger Points Check ---")
            print(f"[DEBUG] Robot location: x={x}, y={y}")
            for gx, gy in danger_points:
                dist = np.linalg.norm(np.array([x, y]) - np.array([gx, gy]))
                print(f"[DEBUG] Danger point: ({gx},{gy}), dist={dist}")
                if dist < 1.0:
                    speed = 0.5
                    print(f"[DEBUG] ==> Robot NEAR danger point: ({gx},{gy}), speed set 0.5")
                    break
            speed_publisher.publish_speed(speed)
        except Exception as e:
            print(f"[LocationTab] Speed publish error: {e}")

    # ... (Các hàm clear_trajectory, update_trajectory, plan_path giữ nguyên như cũ)
    def clear_trajectory(self):
        for item in self.trajectory_items:
            self.map_scene.removeItem(item)
        self.trajectory_items.clear()

    def update_trajectory(self):
        if len(self.trajectory_points) < 2: return
        for item in self.trajectory_items:
            self.map_scene.removeItem(item)
        self.trajectory_items.clear()
        pen = QPen(QColor(180, 0, 0), 3)
        for i in range(len(self.trajectory_points) - 1):
            x1, y1 = self.trajectory_points[i]
            x2, y2 = self.trajectory_points[i + 1]
            line = self.map_scene.addLine(x1, y1, x2, y2, pen)
            self.trajectory_items.append(line)

    def get_goal_names(self):
        return list(self.goals.keys())

    def plan_path(self, goal):
        ref_point = None
        if len(self.last_planned_path) >= 2:
            # Điểm áp chót của lần chạy trước chính là "hướng đi tới" của robot
            ref_point = self.last_planned_path[-2]

        # Gửi tốc độ 1.0 khi bắt đầu hoạch định đường đi
        try:
            from MQTT.publisher_speed import SpeedPublisher
            speed_publisher = SpeedPublisher()
            speed_publisher.publish_speed(1.0)
            print("[DEBUG] Published speed 1.0 at plan_path start")
        except Exception as e:
            print(f"[LocationTab] Speed publish error in plan_path: {e}")

        self.clear_trajectory()
        self.trajectory_points = []
        self.trajectory_times = []

        px, py = self.robot_pos
        self.trajectory_points.append((px, py))
        self.trajectory_times.append(datetime.now())

        self.planned_path = self.planner.find_path(self.robot_pos, goal, ref_point)
        self.planner.draw_path(self.planned_path)
        self.last_planned_path = self.planned_path
        self.plan_points = []

        for px, py in self.planned_path:
            x = self.map_origin[0] + px * self.map_resolution
            y = self.map_origin[1] + (self.map_height - py) * self.map_resolution
            self.plan_points.append({"x": round(x, 3), "y": round(y, 3)})

        curx, cury, _ = self.last_position
        current_wp = {"x": round(curx, 3), "y": round(cury, 3)}
        self.full_plan_points = [current_wp] + self.plan_points

        self.logger.start_logging(self.full_plan_points)

        waypoints_json = json.dumps(self.full_plan_points, indent=2)
        publisher = WaypointsPublisher()
        publisher.publish_waypoints(waypoints_json)