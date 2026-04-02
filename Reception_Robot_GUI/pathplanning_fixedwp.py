# # pathplanning.py
# import numpy as np
# from PyQt6.QtGui import QPen, QColor, QBrush
# from PyQt6.QtCore import Qt, QPointF
# import networkx as nx

# class PathPlanner:
#     def __init__(self, scene):
#         self.scene = scene
#         self.path_items = []
#         self.locations = {}

#         # === n fixed waypoints ===
#         self.fixed_waypoints = { 
#             "wp11": (580, 791),
#             "wp0": (700, 789),
#             "wp1": (822, 780),
#             "wp2": (808, 525),
#             "wp3": (864, 504), 
#             "wp4": (860, 380),
#             "wp5": (850, 304),
#             "wp6": (835, 269),
#             "wp7": (736, 269),
#             "wp8": (750, 306),
#             "wp9": (790, 305),
#             "wp10": (960, 787),
#             "wp12": (860, 385),
#             "wp13": (794, 350),

#         }

#         # === graph ===
#         self.graph_connections = {
#             "wp11": ["wp0"],
#             "wp13": ["wp9"],
#             "wp12": ["wp3", "wp4", "wp5"],
#             "wp0": ["wp1", "wp11"],
#             "wp1": ["wp0", "wp2"],
#             "wp2": ["wp1", "wp3"],
#             "wp3": ["wp2", "wp4"],
#             "wp4": ["wp3", "wp5", "wp9"],
#             "wp5": ["wp4", "wp6", "wp9"],
#             "wp6": ["wp5", "wp7", "wp9"], 
#             "wp7": ["wp6", "wp8"],
#             "wp8": ["wp7", "wp9"],
#             "wp9": ["wp4", "wp5", "wp6", "wp8"],
#             "wp10": ["wp1"]
#         }
#         self._draw_fixed_waypoints()

#     def _draw_fixed_waypoints(self):
#         for name, (x, y) in self.fixed_waypoints.items():
#             r = 4
#             brush = QBrush(QColor(0, 255, 0))
#             pen = QPen(QColor(0, 0, 0), 1)
#             self.scene.addEllipse(x - r, y - r, r * 2, r * 2, pen, brush)
#             text = self.scene.addText(name)
#             text.setDefaultTextColor(QColor(0, 0, 0))
#             text.setPos(x + 12, y - 15)

#     def set_locations(self, locations: dict):
#         self.locations = locations
#         for name, (x, y) in locations.items():
#             self._draw_marker(x, y, name)

#     def _draw_marker(self, x, y, label):
#         r = 6
#         brush = QBrush(QColor(255, 200, 0))
#         pen = QPen(QColor(0, 0, 0), 1)
#         self.scene.addEllipse(x - r, y - r, r * 2, r * 2, pen, brush)
#         text = self.scene.addText(label)
#         text.setDefaultTextColor(QColor(0, 0, 0))
#         text.setPos(x + 10, y - 12)

#     # ======================================================
#     # check if start/goal is on the segment between 2 wp
#     # if start os goal has 1 candidate, check if that candidate wp is between start and goal 
#     # ======================================================
#     def _is_on_segment(self, point, wp1, wp2, tolerance):
#         p = np.array(point)
#         a = np.array(self.fixed_waypoints[wp1])
#         b = np.array(self.fixed_waypoints[wp2])
#         ab = b - a
#         ap = p - a
#         proj = np.dot(ap, ab) / np.dot(ab, ab)
#         if proj < 0 or proj > 1:
#             return False
#         closest = a + proj * ab
#         dist = np.linalg.norm(p - closest)
#         return dist <= tolerance
    
#     def _get_candidates(self, point):
#         candidates = set()

#         # Check if point is on the segment 
#         for wp1, neighbors in self.graph_connections.items():
#             for wp2 in neighbors:
#                 if wp1 >= wp2: continue  # tránh kiểm tra 2 lần
#                 if self._is_on_segment(point, wp1, wp2, tolerance=10):
#                     candidates.add(wp1)
#                     candidates.add(wp2)

#         # if not on the segment, add nearest wp 
#         if not candidates:
#             nearest_wp_name = min(self.fixed_waypoints,
#                                 key=lambda wp: np.linalg.norm(np.array(point) - np.array(self.fixed_waypoints[wp])))
#             candidates.add(nearest_wp_name)
#         return list(candidates)
    
#     def _is_between(self, start, wp, goal, tolerance):
#         s, w, g = np.array(start), np.array(wp), np.array(goal)
        
#         # 1. Phải gần thẳng hàng
#         if np.abs(np.cross(g - s, w - s)) > tolerance:
#             return False
        
#         # 2. wp phải nằm giữa (dot product)
#         dot = np.dot(w - s, g - s)
#         len_sq = np.dot(g - s, g - s)
#         if dot < 0 or dot > len_sq:
#             return False
        
#         return True

# # {"x":14.0,
# # "y":25.5,
# # "theta":0.0}
# # {"x":18.0,
# # "y":1.5,
# # "theta":0.0}
# # {"x":10.0,
# # "y":14.5,
# # "theta":0.0}
# # {"x":20.0,
# # "y":16.5,
# # "theta":0.0}

#     # ==============================
#     # DIJKSTRA + DOUBLE CONSTRAINT (start/goal is on segment of not) 
#     # ==============================
#     def find_path(self, start_px, goal_label):
#         if goal_label not in self.locations:
#             raise ValueError(f"Goal '{goal_label}' not existed")
#         goal_px = self.locations[goal_label]
#         print(f"Finding path {start_px} → {goal_label}:{goal_px}...")

#         # if distance between start and goal is small 
#         distance_pixels = np.linalg.norm(np.array(start_px) - np.array(goal_px))
#         if distance_pixels < 80:  
#             print(f"Distance between start and goal is small ({distance_pixels:.1f}px)")
#             path = [start_px, goal_px]
#             self.draw_path(path)
#             return path

#         # start, goal constraint 
#         start_candidates = self._get_candidates(start_px)
#         print(f"Start candidate: {start_candidates}")
#         goal_candidates = self._get_candidates(goal_px)
#         print(f"Goal candidate: {goal_candidates}")

#         # if start or goal has 1 candidate, we check if they are conlinear 
#         if len(start_candidates) == 1 or len(goal_candidates) == 1:
#             wp_s = self.fixed_waypoints[start_candidates[0]]
#             wp_g = self.fixed_waypoints[goal_candidates[0]]
#             skip_start_wp = self._is_between(start_px, wp_s, goal_px, tolerance=3)
#             skip_goal_wp  = self._is_between(start_px, wp_g, goal_px, tolerance=3)

#             if skip_start_wp or skip_goal_wp:
#                 wp_name = start_candidates[0] if skip_start_wp else goal_candidates[0]
#                 print(f"BỎ QUA wp {wp_name} vì nó nằm giữa đường đi → đi thẳng!")
#                 path = [start_px, goal_px]
#                 self.draw_path(path)
#                 return path
        
#         # graph 
#         G = nx.Graph()
#         for wp1, neighbors in self.graph_connections.items():
#             for wp2 in neighbors:
#                 dist = np.linalg.norm(np.array(self.fixed_waypoints[wp1]) - np.array(self.fixed_waypoints[wp2]))
#                 G.add_edge(wp1, wp2, weight=dist)

#         # find path 
#         best_path = None
#         min_cost = float('inf')

#         for s_wp in start_candidates:
#             for g_wp in goal_candidates:
#                 try:
#                     path = nx.shortest_path(G, source=s_wp, target=g_wp, weight='weight')
#                     cost = nx.shortest_path_length(G, source=s_wp, target=g_wp, weight='weight')
#                     if cost < min_cost:
#                         min_cost = cost
#                         best_path = path
#                 except nx.NetworkXNoPath:
#                     continue

#         if best_path is None:
#             print("No valid path! Going direct.")
#             path_coords = [start_px, goal_px]
#         else:
#             print(f"Optimal wp path: {best_path}")
#             path_coords = [start_px]
#             for wp in best_path:
#                 path_coords.append(self.fixed_waypoints[wp])
#             path_coords.append(goal_px)

#         self.draw_path(path_coords)
#         return path_coords


#     def draw_path(self, path):
#         self.clear_path()
#         if len(path) < 2:
#             return
#         pen = QPen(QColor(255, 0, 0), 1)
#         pen.setStyle(Qt.PenStyle.DashLine)
#         pen.setDashPattern([8, 4])
#         for i in range(len(path) - 1):
#             p1 = QPointF(path[i][0], path[i][1])
#             p2 = QPointF(path[i + 1][0], path[i + 1][1])
#             line = self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
#             self.path_items.append(line)

#     def clear_path(self):
#         for item in self.path_items:
#             self.scene.removeItem(item)
#         self.path_items.clear()

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
            # Cặp waypoint thực tế scan từ map (theo đúng thứ tự)
            "wp1": (203.61, 470.38),
            "wp2": (209.56, 446.60),
            "wp3": (201.45, 400),
            "wp4": (198.76, 289.37),
            "wp5": (194.71, 196.07),
            "wp6": (232.36, 175.70),
            "wp7": (423.03, 168.18),
            "wp8": (607.89, 156.82),
            "wp9": (521.55, 185.83),
            "wp10": (459.69, 226.74),
            "wp11": (917, 436),  
            "wp12": (742, 436),
            "wp13": (416, 461),
        }

        self.graph_connections = {
            "wp1": ["wp2"],
            "wp2": ["wp1", "wp12", "wp3"],  
            "wp3": ["wp12", "wp4"],  # Nhận từ wp12 hoặc wp4
            "wp4": ["wp3", "wp5"],
            "wp5": ["wp4", "wp6"],
            "wp6": ["wp5", "wp7"],
            "wp7": ["wp6", "wp8", "wp9"],
            "wp8": ["wp7", "wp9"],
            "wp9": ["wp7", "wp8", "wp10"],
            "wp10": ["wp9", "wp11"],
            "wp11": ["wp12"],
            "wp12": [ "wp13"],
            "wp13": ["wp1"],
        }

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

        # 🔥 tuning: giảm penalty để robot chọn waypoint safety chứ không đều đường thẳng nguy hiểm
        if angle > 120:
            return 30    # quay đầu → phạt nhẹ
        elif angle > 60:
            return 10    # rẽ vừa → phạt rất nhẹ
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

    def _normalize_name(self, name: str):
        key = "goal_" + "".join(c.lower() if c.isalnum() else "_" for c in name)
        return key

    def _find_nearest_waypoints(self, x, y, k=3):
        candidates = []
        for wp_name, (wx, wy) in self.fixed_waypoints.items():
            dist = np.linalg.norm(np.array((wx, wy)) - np.array((x, y)))
            candidates.append((dist, wp_name))
        candidates.sort(key=lambda e: e[0])
        return [wp for _, wp in candidates[:k]]

    def _remove_goal_nodes(self):
        for node in list(getattr(self, 'goal_nodes', [])):
            self.fixed_waypoints.pop(node, None)
            if node in self.graph_connections:
                self.graph_connections.pop(node, None)
            for neighbors in self.graph_connections.values():
                if node in neighbors:
                    neighbors.remove(node)
        self.goal_nodes = set()

    def set_locations(self, locations: dict):
        self.locations = locations

        # xóa goal nodes cũ (nếu set_locations đã chạy trước đó)
        self._remove_goal_nodes()

        for name, (x, y) in locations.items():
            goal_node = self._normalize_name(name)
            self.goal_nodes.add(goal_node)
            self.fixed_waypoints[goal_node] = (x, y)

            # Gắn điểm arrival (goal) vào đồ thị bằng cách liên kết tới 3 waypoint gần nhất
            nearest = self._find_nearest_waypoints(x, y, k=3)
            self.graph_connections.setdefault(goal_node, [])
            for n in nearest:
                if n == goal_node:
                    continue
                if n not in self.graph_connections.get(goal_node, []):
                    self.graph_connections[goal_node].append(n)
                self.graph_connections.setdefault(n, [])
                if goal_node not in self.graph_connections[n]:
                    self.graph_connections[n].append(goal_node)

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
        visited = set()

        while queue:
            cost, current, prev, path = heapq.heappop(queue)

            if current in visited:
                continue
            visited.add(current)

            path = path + [current]

            if current == goal:
                return path, cost

            for neighbor in self.graph_connections.get(current, []):
                if neighbor in visited:
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
    def _resolve_goal_label(self, goal_label):
        if goal_label in self.locations:
            return goal_label

        normalized = goal_label.strip().casefold()
        for name in self.locations.keys():
            if name.strip().casefold() == normalized:
                return name

        raise ValueError(f"Goal '{goal_label}' not existed")

    def find_path(self, start_px, goal_label):
        goal_key = self._resolve_goal_label(goal_label)
        goal_px = self.locations[goal_key]

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