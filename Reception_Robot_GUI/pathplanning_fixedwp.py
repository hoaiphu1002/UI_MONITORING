# pathplanning.py
import numpy as np
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtCore import Qt, QPointF
import networkx as nx

class PathPlanner:
    def __init__(self, scene):
        self.scene = scene
        self.path_items = []
        self.locations = {}

        self.fixed_waypoints = { 
            "wp11": (580, 791),
            "wp0": (700, 789),
            "wp1": (822, 780),
            "wp2": (808, 525),
            "wp3": (864, 504), 
            "wp4": (860, 380),
            "wp5": (850, 304),
            "wp6": (835, 269),
            "wp7": (736, 269),
            "wp8": (750, 306),
            "wp9": (790, 305),
            "wp10": (960, 787),
            "wp12": (860, 385),
            "wp13": (794, 350),
        }

        self.graph_connections = {
            "wp11": ["wp0"],
            "wp13": ["wp9"],
            "wp12": ["wp3", "wp4", "wp5"],
            "wp0": ["wp1", "wp11"],
            "wp1": ["wp0", "wp2"],
            "wp2": ["wp1", "wp3"],
            "wp3": ["wp2", "wp4"],
            "wp4": ["wp3", "wp5", "wp9"],
            "wp5": ["wp4", "wp6", "wp9"],
            "wp6": ["wp5", "wp7", "wp9"], 
            "wp7": ["wp6", "wp8"],
            "wp8": ["wp7", "wp9"],
            "wp9": ["wp4", "wp5", "wp6", "wp8"],
            "wp10": ["wp1"]
        }

        # Chuyển sang đồ thị không hướng (hai chiều) để tìm đường tuần tự đúng
        for wp, neighbours in list(self.graph_connections.items()):
            for n in neighbours:
                self.graph_connections.setdefault(n, [])
                if wp not in self.graph_connections[n]:
                    self.graph_connections[n].append(wp)

        self._draw_fixed_waypoints()

    # =========================
    # 🔥 NEW: tính góc đổi hướng
    # =========================
    def _angle_penalty(self, prev, curr, next):
        if prev is None:
            return 0

        v1 = np.array(curr) - np.array(prev)
        v2 = np.array(next) - np.array(curr)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0

        cos_theta = np.dot(v1, v2) / (norm1 * norm2)
        cos_theta = np.clip(cos_theta, -1, 1)
        angle = np.degrees(np.arccos(cos_theta))

        # 🔥 tuning
        if angle > 120:
            return 200   # quay đầu → phạt nặng
        elif angle > 60:
            return 50    # rẽ vừa
        else:
            return 0     # đi thẳng

    def _draw_fixed_waypoints(self):
        for name, (x, y) in self.fixed_waypoints.items():
            r = 4
            brush = QBrush(QColor(0, 255, 0))
            pen = QPen(QColor(0, 0, 0), 1)
            self.scene.addEllipse(x - r, y - r, r * 2, r * 2, pen, brush)
            text = self.scene.addText(name)
            text.setDefaultTextColor(QColor(0, 0, 0))
            text.setPos(x + 12, y - 15)

    def set_locations(self, locations: dict):
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
        text.setPos(x + 10, y - 12)

    def _is_on_segment(self, point, wp1, wp2, tolerance):
        p = np.array(point)
        a = np.array(self.fixed_waypoints[wp1])
        b = np.array(self.fixed_waypoints[wp2])
        ab = b - a
        ap = p - a
        proj = np.dot(ap, ab) / np.dot(ab, ab)
        if proj < 0 or proj > 1:
            return False
        closest = a + proj * ab
        dist = np.linalg.norm(p - closest)
        return dist <= tolerance
    
    def _get_candidates(self, point):
        candidates = set()

        for wp1, neighbors in self.graph_connections.items():
            for wp2 in neighbors:
                if wp1 >= wp2: continue
                if self._is_on_segment(point, wp1, wp2, tolerance=10):
                    candidates.add(wp1)
                    candidates.add(wp2)

        if not candidates:
            nearest_wp_name = min(self.fixed_waypoints,
                                key=lambda wp: np.linalg.norm(np.array(point) - np.array(self.fixed_waypoints[wp])))
            candidates.add(nearest_wp_name)
        return list(candidates)

    # =========================
    # 🔥 NEW: custom Dijkstra
    # =========================
    def _dijkstra_with_heading(self, start, goal):
        import heapq

        queue = [(0, start, None, [])]  # cost, current, prev, path
        visited = set()  # lưu trạng thái (current, prev)

        while queue:
            cost, current, prev, path = heapq.heappop(queue)

            state = (current, prev)
            if state in visited:
                continue
            visited.add(state)

            path = path + [current]

            if current == goal:
                return path, cost

            for neighbor in self.graph_connections.get(current, []):
                next_state = (neighbor, current)
                if next_state in visited:
                    continue

                curr_pos = self.fixed_waypoints[current]
                next_pos = self.fixed_waypoints[neighbor]

                dist = np.linalg.norm(np.array(curr_pos) - np.array(next_pos))
                penalty = self._angle_penalty(
                    self.fixed_waypoints[prev] if prev else None,
                    curr_pos,
                    next_pos
                )

                new_cost = cost + dist + penalty

                heapq.heappush(queue, (new_cost, neighbor, current, path))

        return None, float('inf')

    # =========================
    # MAIN
    # =========================
    def find_path(self, start_px, goal_label):
        if goal_label not in self.locations:
            raise ValueError(f"Goal '{goal_label}' not existed")

        goal_px = self.locations[goal_label]

        start_candidates = self._get_candidates(start_px)
        goal_candidates = self._get_candidates(goal_px)

        best_path = None
        min_cost = float('inf')

        for s_wp in start_candidates:
            for g_wp in goal_candidates:
                path, cost = self._dijkstra_with_heading(s_wp, g_wp)
                if path and cost < min_cost:
                    min_cost = cost
                    best_path = path

        if best_path is None:
            path_coords = [start_px, goal_px]
        else:
            path_coords = [start_px]
            for wp in best_path:
                path_coords.append(self.fixed_waypoints[wp])
            path_coords.append(goal_px)

        self.draw_path(path_coords)
        return path_coords

    def draw_path(self, path):
        self.clear_path()
        if len(path) < 2:
            return
        pen = QPen(QColor(255, 0, 0), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([8, 4])
        for i in range(len(path) - 1):
            p1 = QPointF(path[i][0], path[i][1])
            p2 = QPointF(path[i + 1][0], path[i + 1][1])
            line = self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            self.path_items.append(line)

    def clear_path(self):
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear()