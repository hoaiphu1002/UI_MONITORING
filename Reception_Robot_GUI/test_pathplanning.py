from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QPushButton, QVBoxLayout, QWidget, QComboBox
from PyQt6.QtGui import QPixmap, QBrush, QPen, QColor, QPolygonF
from PyQt6.QtCore import Qt, QPointF
from pathplanning import PathPlanner
import sys

class MapWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Path Planning on Real Map")
        self.resize(800, 800)

        # --- Layout ---
        layout = QVBoxLayout(self)
        self.view = QGraphicsView()
        layout.addWidget(self.view)

        self.selector = QComboBox()
        self.selector.addItems(["A", "B", "C", "D"])
        layout.addWidget(self.selector)

        self.btn_plan = QPushButton("Find Path")
        layout.addWidget(self.btn_plan)

        # --- Scene + Map ---
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.map_pix = QPixmap("Reception_Robot_GUI/resources/Map/new_map2.pgm")
        self.scene.addPixmap(self.map_pix)

        # --- Path planner ---
        self.planner = PathPlanner(self.scene)
        # self.planner.load_cost_map("Reception_Robot_GUI/resources/Map/new_map2.pgm")

        # điểm cố định (pixel)
        self.planner.set_locations({
            " 1": (821, 763),
            " 2": (804, 545),
            " 3": (866, 504),
            " 4": (860, 377),
            " 5": (835, 269),
            " 6": (736, 273),
            " 7": (735, 306),
            " 8": (850, 304)
        })

        # Vị trí robot hiện tại (pixel)
        self.robot_pos = (971, 800)
        robot_shape = QPolygonF([
            QPointF(0, -10),
            QPointF(6, 10),
            QPointF(-6, 10)
        ])
        self.robot_item = self.scene.addPolygon(robot_shape, QPen(Qt.GlobalColor.black), QBrush(QColor(0, 200, 255)))
        self.robot_item.setPos(*self.robot_pos)

        # --- Event ---
        self.btn_plan.clicked.connect(self.plan_path)

    def plan_path(self):
        """Khi bấm nút Find Path"""
        goal = self.selector.currentText()
        path = self.planner.find_path(self.robot_pos, goal)
        self.planner.draw_path(path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MapWindow()
    w.show()
    sys.exit(app.exec())
