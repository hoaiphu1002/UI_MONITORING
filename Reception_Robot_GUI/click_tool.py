import sys
import yaml
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMainWindow
from PyQt6.QtGui import QPixmap, QMouseEvent, QPainter
from PyQt6.QtCore import Qt, QRectF

class MapClickView(QGraphicsView):
    def __init__(self, map_path):
        super().__init__()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)

        # 1. Load ảnh map
        self.scene = QGraphicsScene()
        pixmap = QPixmap(map_path)
        if pixmap.isNull():
            print(f"❌ Không thể load ảnh tại: {map_path}")
            sys.exit(1)

        self.scene.addPixmap(pixmap)
        self.setScene(self.scene)
        self.setSceneRect(QRectF(pixmap.rect()))

        self.map_width = pixmap.width()
        self.map_height = pixmap.height()

        # 2. Đọc cấu hình YAML
        yaml_path = map_path.replace(".pgm", ".yaml")
        try:
            with open(yaml_path, 'r') as file:
                map_config = yaml.safe_load(file)
                self.map_resolution = map_config['resolution']
                self.map_origin = (map_config['origin'][0], map_config['origin'][1])
                print(f"✅ Đã tải YAML: Resolution={self.map_resolution}, Origin={self.map_origin}")
        except Exception as e:
            print(f"⚠️ Lỗi đọc YAML: {e}. Dùng thông số mặc định.")
            self.map_resolution = 0.05
            self.map_origin = (0.0, 0.0)

        # 3. Thực hiện chuyển đổi danh sách Waypoints từ XML (Yêu cầu của bạn)
        self.convert_xml_waypoints()

    def convert_xml_waypoints(self):
        # Dữ liệu từ file XML của bạn
        wx = [-0.0145568176766, 4.07109296558, 4.36828805066, 3.96287388499, 3.82816284655, 
              3.6259261503, 5.50858533119, 15.0417906024, 25.405224311]
        wy = [-0.0899522513034, 0.226667157814, 1.41586392363, 4.92082046796, 9.27709200749, 
              13.9424737858, 14.9608998089, 15.3367562076, 16.1181246676]

        print("\n" + "="*60)
        print("🤖 KẾT QUẢ CHUYỂN ĐỔI XML -> PIXEL (Dán vào PathPlanner):")
        print("="*60)
        for i, (mx, my) in enumerate(zip(wx, wy)):
            px = (mx - self.map_origin[0]) / self.map_resolution
            py = self.map_height - (my - self.map_origin[1]) / self.map_resolution
            print(f'            "wp{i}": ({int(px)}, {int(py)}),')
        print("="*60 + "\n")
        print("👉 Bây giờ bạn có thể CLICK lên bản đồ để lấy thêm tọa độ lẻ...")

    def mousePressEvent(self, event: QMouseEvent):
        """ Giữ nguyên chức năng chọn tọa độ từ màn hình """
        if event.button() == Qt.MouseButton.LeftButton:
            # Lấy vị trí click trên Scene
            scene_pos = self.mapToScene(event.position().toPoint())
            px, py = int(scene_pos.x()), int(scene_pos.y())

            # Chuyển ngược sang tọa độ /map (mét) để kiểm tra
            mx = px * self.map_resolution + self.map_origin[0]
            my = (self.map_height - py) * self.map_resolution + self.map_origin[1]

            print(f"📍 [CLICKED] Pixel: ({px}, {py})  ===>  Map: ({mx:.3f}m, {my:.3f}m)")

        super().mousePressEvent(event)

class MapClickWindow(QMainWindow):
    def __init__(self, map_path):
        super().__init__()
        self.setWindowTitle("Map To Pixel Converter & Picker")
        self.resize(1100, 850)
        self.map_view = MapClickView(map_path)
        self.setCentralWidget(self.map_view)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Thay đổi đường dẫn file .pgm của bạn ở đây
    map_file = "Reception_Robot_GUI/resources/Map/B2_map.pgm" 
    window = MapClickWindow(map_file)
    window.show()
    sys.exit(app.exec())