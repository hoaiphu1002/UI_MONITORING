from skimage import io, color, graph, draw
import numpy as np
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtCore import QPointF
import matplotlib.path as mpltPath
from scipy.ndimage import binary_dilation
from rdp import rdp

class PathPlanner:
    def __init__(self, scene):
        """
        scene: QGraphicsScene 
        """
        self.scene = scene
        self.cost_map = None
        self.path_items = []
        self.locations = {}


    def load_cost_map(self, map_path):
        img = io.imread(map_path)  # .pgm la grayscale 
        img = img.astype(np.uint8)  # 0-255

        cost = np.ones_like(img, dtype=float)  # Cost map 
        obstacle = img < 50 
        unknown = (img >= 50)&(img < 210)
        available = img >= 210

        # Gán chi phí 
        cost[obstacle] = 1e6
        cost[unknown] = 1e5 
        cost[available] = 1.0

        # buffer zone 
        dilated_mask = binary_dilation(obstacle, iterations=8)
        cost[dilated_mask] = 1e6

        '''Sau day la tao mask cho map (thuc te thi k di duoc du quet map trong)'''
        polygon_unknown = [
            [   [754, 721],  #area 1 
                [964, 832],
                [615, 1412],
                [404, 1294]],
            [   [989, 801],  #area 2 
                [1363, 171],
                [1158, 49],
                [776, 679],],
            [   [765, 635],  #area 3
                [659, 576],
                [628, 621],
                [729, 683]],
            [   [641, 1416],  #area 4
                [974, 1228],
                [1009, 832],
                [1384, 185]],
            [   [984, 803],  #area 5
                [1356, 164],
                [1170, 88],
                [790, 674]]
        ]
        for each in polygon_unknown:
            path = mpltPath.Path(each)
            y_coords, x_coords = np.mgrid[:cost.shape[0], :cost.shape[1]]
            points = np.column_stack([x_coords.ravel(), y_coords.ravel()])
            mask = path.contains_points(points).reshape(cost.shape)
            cost[mask] = 1e5 
            dilated_mask = binary_dilation(mask, iterations=8)
            cost[dilated_mask] = 1e5

        self.cost_map = cost
        
        
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 8))
        plt.imshow(self.cost_map, cmap='hot')
        plt.colorbar(label='Chi phí')
        plt.title('Cost Map')
        plt.show()
        
        
    def set_locations(self, locations: dict):
        """sei 4 goals A,B,C,D (pixel-based)"""
        self.locations = locations
        for name, (x, y) in locations.items():
            self._draw_marker(x, y, name)


    def _draw_marker(self, x, y, label):
        r = 6
        brush = QBrush(QColor(255, 200, 0))
        pen = QPen(QColor(0, 0, 0), 1)
        self.scene.addEllipse(x - r, y - r, r * 2, r * 2, pen, brush)
        text = self.scene.addText(label)
        text.setDefaultTextColor(QColor(0, 0, 0))
        text.setPos(x + 8, y - 10)


    def find_path(self, start_px, goal_label):
        if self.cost_map is None:
            raise RuntimeError("Cost map not found")
        if goal_label not in self.locations:
            raise ValueError(f"Goal '{goal_label}' not existed")

        goal = self.locations[goal_label]
        start = (int(start_px[1]), int(start_px[0]))  # (row, col)
        end = (int(goal[1]), int(goal[0]))            # (row, col)

        print(f"Finding path {start_px} → {goal_label}:{goal}...")

        # Tìm đường đi bằng skimage.graph
        try:
            path, cost = graph.route_through_array(
                self.cost_map,
                start=start,
                end=end,
                fully_connected=True,
                geometric=True
            )
        except Exception as e:
            print(f"[PathPlanner] Error: {e}")
            return []

        path = np.array(path)
        print(f"[PathPlanner] Path length: {len(path)} | total cost = {cost:.2f}")

        # smoothing path 
        if len(path) > 2: 
            simplified_path = rdp(path, epsilon=22.5) 
            self.draw_path(simplified_path)
            return simplified_path
        else:
            self.draw_path(path)
            return path


    def draw_path(self, path):
        self.clear_path()
        pen = QPen(QColor(255, 0, 0), 2)
        for i in range(len(path) - 1):
            p1 = QPointF(path[i][1], path[i][0])
            p2 = QPointF(path[i + 1][1], path[i + 1][0])
            line = self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            self.path_items.append(line)

    def clear_path(self):
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear()
