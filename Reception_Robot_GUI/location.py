from PyQt6.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QGraphicsPolygonItem, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap, QPolygonF, QWheelEvent, QPainter, QBrush, QPen, QColor
from PyQt6.QtCore import QPointF, Qt, QTimer
import yaml, json
import numpy as np
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

        # 1. Tọa độ Home mong muốn (Pixel)
        self.home_px = 825
        self.home_py = 394

        # 2. PHẢI LOAD MAP TRƯỚC (Để lấy resolution và origin từ YAML)
        self.load_map("Reception_Robot_GUI/resources/Map/new_map2.pgm")

        # 3. TÍNH TOÁN VỊ TRÍ BAN ĐẦU (Chuyển Pixel Home -> Mét)
        # Công thức tính tọa độ thực từ pixel
        init_x = self.map_origin[0] + (self.home_px * self.map_resolution)
        init_y = self.map_origin[1] + (self.map_height - self.home_py) * self.map_resolution
        
        # Gán vị trí ban đầu là Home
        self.last_position = [init_x, init_y, 0.0]

        # 4. TẠO ROBOT VÀ VẼ LÊN UI NGAY LẬP TỨC
        self.create_robot()
        self.update_robot_gui() 

        # Goals (Danh sách điểm đến)
        self.goals = {
            "Restroom": (717, 505),
            "Water intake": (736, 269),
            "Home": (self.home_px, self.home_py),
            "Chemistry hall": (835, 269),
            "Robotics lab": (464, 792),
            "Stairs": (820, 727),
            "Electrical lab": (1116, 778),
        }

        # Khởi tạo trajectory với điểm Home là điểm đầu tiên
        self.trajectory_points = [(self.home_px, self.home_py)]
        self.trajectory_times = [datetime.now()]
        self.trajectory_items = []

        # Timer cập nhật vị trí từ MQTT (nếu có)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_robot_gui)
        self.update_timer.start(100)

        # Path planner
        self.planner = PathPlanner(self.map_scene)
        self.planner.set_locations(self.goals)

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

        # Lưu vết đường đi (Trajectory)
        if hasattr(self, 'trajectory_points') and len(self.trajectory_points) > 0:
            current_point = (px, py)
            last_point = self.trajectory_points[-1]

            if np.linalg.norm(np.array(current_point) - np.array(last_point)) > 2:
                self.trajectory_points.append(current_point)
                self.trajectory_times.append(datetime.now())
                self.update_trajectory()

    def set_location(self, x, y, theta):
        """Hàm này nhận dữ liệu x, y, theta từ MQTT Manager"""
        self.last_position = [x, y, theta]

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
        self.clear_trajectory()
        self.trajectory_points = []
        self.trajectory_times = []
        px, py = self.robot_pos
        self.trajectory_points.append((px, py))
        self.trajectory_times.append(datetime.now())
        self.planned_path = self.planner.find_path(self.robot_pos, goal)
        self.planner.draw_path(self.planned_path)
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