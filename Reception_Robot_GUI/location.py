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
    def __init__(self, view):
        super().__init__()
        self.ui = view
        
        # Flag bảo vệ để không xung đột khi đang tính toán đường đi
        self._is_planning = False 

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

        self.trajectory_items = []
        self.trajectory_points = []
        self.trajectory_times = []

        # Path planner
        self.planner = PathPlanner(self.map_scene)
        self.goals = self.planner.goals 
        
        home_coords = self.goals.get("Home", (121, 476))
        self.home_px, self.home_py = home_coords

        # Load map (Thay đổi đường dẫn file nếu cần)
        self.load_map("Reception_Robot_GUI/resources/Map/B2_map.pgm")
        
        # Khởi tạo vị trí ban đầu
        init_x = self.map_origin[0] + (self.home_px * self.map_resolution)
        init_y = self.map_origin[1] + (self.map_height - self.home_py) * self.map_resolution

        self.last_position = [init_x, init_y, 0.0]
        self._display_heading_deg = 0.0
        self._last_px_py = None
        
        self.create_robot()
        self.update_robot_gui()
        
        self.last_planned_path = []
        
        # Timer cập nhật GUI
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_robot_gui)
        self.update_timer.start(100)

    # ==========================================
    #                  MAP & ROBOT
    # ==========================================
    def load_map(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
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
        except Exception:
            self.map_resolution = 0.05
            self.map_origin = (-1.545, -12.181) 

    def create_robot(self):
        pixmap = QPixmap("Reception_Robot_GUI/resources/Icons/robot.png")
        pixmap = pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        self.robot_item = QGraphicsPixmapItem(pixmap)
        self.robot_item.setZValue(100)
        self.robot_w, self.robot_h = pixmap.width(), pixmap.height()
        self.robot_item.setTransformOriginPoint(self.robot_w / 2, self.robot_h / 2)
        self.robot_icon_forward_offset_deg = 90.0
        self.map_scene.addItem(self.robot_item)

        # Heading indicator (Mũi tên đỏ)
        self.heading_line = self.map_scene.addLine(0, 0, 0, 0, QPen(QColor(255, 0, 0), 3))
        self.heading_line.setZValue(110)
        self.heading_arrow = QGraphicsPolygonItem()
        self.heading_arrow.setBrush(QBrush(QColor(255, 0, 0)))
        self.heading_arrow.setPen(QPen(Qt.GlobalColor.transparent, 0))
        self.heading_arrow.setZValue(111)
        self.map_scene.addItem(self.heading_arrow)

    def update_robot_gui(self):
        x, y, theta = self.last_position
        px = (x - self.map_origin[0]) / self.map_resolution
        py = self.map_height - (y - self.map_origin[1]) / self.map_resolution

        self.robot_pos = (px, py)
        self.robot_item.setPos(px - self.robot_w/2, py - self.robot_h/2)

        # Logic hiển thị hướng: ưu tiên hướng di chuyển thực tế nếu có
        movement_heading = None
        if self._last_px_py is not None:
            dx, dy = px - self._last_px_py[0], py - self._last_px_py[1]
            if math.hypot(dx, dy) > 0.8: # Chỉ tính hướng khi robot di chuyển rõ rệt
                movement_heading = math.degrees(math.atan2(dy, dx))

        self._display_heading_deg = movement_heading if movement_heading is not None else self._theta_to_scene_deg(theta)
        self._update_heading_indicator(px, py, self._display_heading_deg)
        self.robot_item.setRotation(self._display_heading_deg + self.robot_icon_forward_offset_deg)
        
        # Vẽ vết đường đi
        if len(self.trajectory_points) > 0:
            if math.dist((px, py), self.trajectory_points[-1]) > 2:
                self.trajectory_points.append((px, py))
                self.update_trajectory()

        self._last_px_py = (px, py)

    def _theta_to_scene_deg(self, theta):
        deg = math.degrees(theta) if abs(theta) <= (2 * math.pi + 0.1) else theta
        return -deg

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

    def set_location(self, x, y, theta):
        self.last_position = [x, y, theta]

    # ==========================================
    #           PATH PLANNING & MQTT
    # ==========================================
    def plan_path(self, goal):
        # Tránh xung đột nếu đang trong quá trình tính toán
        if self._is_planning:
            return
        self._is_planning = True

        try:
            ref_point = self.last_planned_path[-2] if len(self.last_planned_path) >= 2 else None
            self.clear_trajectory()
            self.trajectory_points = [(self.robot_pos)]

            # Tìm đường đi từ PathPlanner
            self.planned_path = self.planner.find_path(self.robot_pos, goal, ref_point)
            self.planner.draw_path(self.planned_path)
            self.last_planned_path = self.planned_path
            
            # Chuyển đổi sang tọa độ thực (m)
            self.plan_points = []
            for p_px, p_py in self.planned_path:
                x = self.map_origin[0] + p_px * self.map_resolution
                y = self.map_origin[1] + (self.map_height - p_py) * self.map_resolution
                self.plan_points.append({"x": round(x, 3), "y": round(y, 3)})

            # Kết hợp vị trí hiện tại và lọc điểm trùng
            curx, cury, _ = self.last_position
            current_wp = {"x": round(curx, 3), "y": round(cury, 3)}
            self.full_plan_points = self._dedupe_waypoints([current_wp] + self.plan_points)

            # Gửi MQTT và Log
            self.logger.start_logging(self.full_plan_points)
            WaypointsPublisher().publish_waypoints(json.dumps(self.full_plan_points, indent=2))

        finally:
            # Giải phóng khóa sau 500ms
            QTimer.singleShot(500, self._unlock_planning)

    def _unlock_planning(self):
        self._is_planning = False

    def _dedupe_waypoints(self, points):
        """Loại bỏ các điểm tọa độ giống hệt nhau liên tiếp"""
        if not points: return []
        deduped = [points[0]]
        for i in range(1, len(points)):
            if points[i] != points[i-1]:
                deduped.append(points[i])
        return deduped

    def clear_trajectory(self):
        for item in self.trajectory_items:
            self.map_scene.removeItem(item)
        self.trajectory_items.clear()

    def update_trajectory(self):
        if len(self.trajectory_points) < 2: return
        self.clear_trajectory()
        pen = QPen(QColor(180, 0, 0), 2, Qt.PenStyle.DotLine)
        for i in range(len(self.trajectory_points) - 1):
            p1, p2 = self.trajectory_points[i], self.trajectory_points[i+1]
            self.trajectory_items.append(self.map_scene.addLine(p1[0], p1[1], p2[0], p2[1], pen))

    def get_goal_names(self):
        return list(self.goals.keys())