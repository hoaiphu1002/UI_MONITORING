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
            "Restroom": (717, 505),
            "Water intake": (736, 269),
            "Chemistry hall": (835, 269),
            "Robotics lab": (464, 792),
            "Stairs": (820, 727),
            "Electrical lab": (1116, 778),
            "Home": (825, 394)
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

        # tupple_x = [17.6858554792, 16.8749998552, 19.9679920085, 19.6681547578, 18.4091273325, 13.4507733824, 13.4117297827, 19.1596853144, 19.66815475, 19.96799200, 16.87499985, 17.68585547]
        # tupple_y = [1.52747189432,  12.4088992202, 14.4544250146, 20.8412712994, 26.2399740808, 26.0336352831, 24.3740114849, 24.5011076441, 20.84127129, 14.45442501, 12.4088992202, 1.527471894]

        # for i, (x, y) in enumerate(zip(tupple_x, tupple_y), 1):
        #     py = self.map_height - (y - self.map_origin[1]) / self.map_resolution 
        #     px = (x - self.map_origin[0]) / self.map_resolution 
        #     print(f'"{i:2d}": ({int(px)}, {int(py)}),')


class MapClickWindow(QMainWindow):
    def __init__(self, map_path):
        super().__init__()
        self.setWindowTitle("Map Click Tool")
        self.resize(800, 600)
        self.map_view = MapClickView(map_path)
        self.setCentralWidget(self.map_view)
        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    map_path = "Reception_Robot_GUI/resources/Map/new_map2.pgm"
    window = MapClickWindow(map_path)
    window.show()
    sys.exit(app.exec())
