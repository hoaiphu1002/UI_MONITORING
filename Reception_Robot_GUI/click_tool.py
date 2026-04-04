import sys
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMainWindow
from PyQt6.QtGui import QPixmap, QMouseEvent, QPainter
from PyQt6.QtCore import Qt, QRectF
import yaml

class MapClickView(QGraphicsView):
    def __init__(self, map_path):
        super().__init__()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)  # ❌ Không cho kéo
        self.setMouseTracking(True)

        # Load ảnh map
        self.scene = QGraphicsScene()
        pixmap = QPixmap(map_path)
        if pixmap.isNull():
            print(f"Không thể load ảnh: {map_path}")
            sys.exit(1)

        self.scene.addPixmap(pixmap)
        self.setScene(self.scene)
        self.setSceneRect(QRectF(pixmap.rect()))  # ✅ Ép kiểu QRect → QRectF

        # Lưu thông tin ảnh
        self.map_width = pixmap.width()
        self.map_height = pixmap.height()

        # Đọc thông số từ file map.yaml
        yaml_path = map_path.replace(".pgm", ".yaml")
        try:
            with open(yaml_path, 'r') as file:
                map_config = yaml.safe_load(file)
                self.map_resolution = map_config['resolution']
                self.map_origin = (map_config['origin'][0], map_config['origin'][1])
                print(f"Loaded map config - resolution: {self.map_resolution}, origin: {self.map_origin}")
        except Exception as e:
            print(f"Error while reading {yaml_path}: {e}")
            self.map_resolution = 0.05  # Giá trị mặc định nếu không đọc được
            self.map_origin = (0.0, 0.0)

        print(f"Map loaded: {pixmap.width()}x{pixmap.height()} pixels")
        print("Click lên bản đồ để lấy tọa độ pixel")
        # Danh sách cần chuyển đổi
        my_pixels = {
            "Home": [121, 476], 
            "Thư viện": [120, 402],
            "Sân banh": [148, 628],

            "Phòng họp": [200, 169],
            "Nhà vệ sinh": [265, 167],
            "PTN vi sinh": [423, 168], 
            
            "Lab CEPP": [630, 152], 
            "Home 2": [944, 468],
            "PTN hóa lý": [558, 448]
        }
        
        print("\n=== ĐANG CHUYỂN ĐỔI DANH SÁCH GOALS ===")
        for name, (px, py) in my_pixels.items():
            # Áp dụng công thức có sẵn trong class
            mx = px * self.map_resolution + self.map_origin[0]
            my = (self.map_height - py) * self.map_resolution + self.map_origin[1]
            print(f'"{name}": ({mx:.3f}, {my:.3f}),')
    def mousePressEvent(self, event: QMouseEvent):

        x = 17.9232163663
        y = 19.9541592458
        py = self.map_height - (y - self.map_origin[1]) / self.map_resolution 
        px = (x - self.map_origin[0]) / self.map_resolution 
        print(f"Example conversion: ({x}, {y})m → ({int(px)}, {int(py)}) pixels")

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            x_pixel, y_pixel = int(scene_pos.x()), int(scene_pos.y())
            print(f"📍 Click tại pixel: ({x_pixel}, {y_pixel})")

            # Chuyển từ pixel sang tọa độ /map
            y_map = (self.map_height - y_pixel) * self.map_resolution + self.map_origin[1]
            x_map = x_pixel * self.map_resolution + self.map_origin[0]
            print(f"   Tọa độ /map: ({x_map:.2f}, {y_map:.2f})m")
            
        super().mousePressEvent(event)

class MapClickWindow(QMainWindow):
    def __init__(self, map_path):
        super().__init__()
        self.setWindowTitle("Map Click Tool")
        self.resize(800, 600)
        self.map_view = MapClickView(map_path)
        self.setCentralWidget(self.map_view)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    map_path = "Reception_Robot_GUI/resources/Map/B2_map.pgm"
    window = MapClickWindow(map_path)
    window.show()
    sys.exit(app.exec())
