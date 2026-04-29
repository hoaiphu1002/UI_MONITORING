import numpy as np
import networkx as nx
import json
import math
from PyQt6.QtGui import QPen, QColor, QBrush, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsTextItem

class PathPlanner:
    def __init__(self, scene, config_path="Reception_Robot_GUI/resources/Map/B2_config_wp.json"):
        self.scene = scene
        self.path_items = []
        self._no_path_text_item = None
        
        # Load dữ liệu từ JSON
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        self.waypoints = config['waypoints']
        self.goals = config['goals']
        self.connections = config['connections']
        
        # Hợp nhất tất cả các điểm
        self.all_nodes = {**self.waypoints, **self.goals}
        
        # Xây dựng Đồ thị điểm (Node Graph) đơn giản
        self._build_simple_graph()
        self._draw_fixed_points()

    def _draw_angle_visual(self, prev, center, next, angle_deg, sign, normalized_angle=None):
        """Vẽ visual hóa góc lệch giữa 3 điểm trên scene và hiển thị giá trị góc lệch ngay trên bản đồ."""
        pen1 = QPen(QColor(0, 0, 255), 2)
        pen2 = QPen(QColor(0, 200, 0), 2)
        
        self.scene.addLine(prev[0], prev[1], center[0], center[1], pen1)
        self.scene.addLine(center[0], center[1], next[0], next[1], pen2)
        
        if hasattr(self, '_angle_text_item') and self._angle_text_item is not None:
            self.scene.removeItem(self._angle_text_item)
            
        text = f"Góc lệch: {normalized_angle if normalized_angle is not None else int(angle_deg)}°"
        self._angle_text_item = QGraphicsTextItem(text)
        self._angle_text_item.setDefaultTextColor(QColor(255, 0, 0))
        self._angle_text_item.setFont(QFont("Roboto", 7, QFont.Weight.Bold))
        self._angle_text_item.setPos(center[0]+10, center[1]-30)
        self.scene.addItem(self._angle_text_item)

    def _compute_angle_between(self, prev, center, next):
        """Tính góc (độ), dấu (xoay trái/phải), dot product giữa 3 điểm."""
        v1 = np.array(center) - np.array(prev)
        v2 = np.array(next) - np.array(center)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0, 1, 1.0
        v1n = v1 / norm1
        v2n = v2 / norm2
        dot = np.clip(np.dot(v1n, v2n), -1.0, 1.0)
        angle = np.arccos(dot)
        cross = v1n[0]*v2n[1] - v1n[1]*v2n[0]
        sign = 1 if cross >= 0 else -1
        angle_deg = np.degrees(angle)
        return angle_deg, sign, dot

    def _build_simple_graph(self):
        """Xây dựng Node Graph: Các nút là điểm, cạnh là khoảng cách vật lý"""
        self.graph = nx.DiGraph() 
        
        for u in self.connections:
            for v in self.connections.get(u, []):
                dist = np.linalg.norm(np.array(self.all_nodes[u]) - np.array(self.all_nodes[v]))
                self.graph.add_edge(u, v, weight=dist)

    def _get_candidates(self, point):
        """Lấy 3 điểm (nodes) gần với vị trí hiện tại nhất"""
        dist_to_point = lambda name: np.linalg.norm(np.array(point) - np.array(self.all_nodes[name]))
        candidates = sorted(self.all_nodes.keys(), key=dist_to_point)
        return candidates[:3] 

    def _show_no_path_warning(self, pos):
        """Hiển thị cảnh báo không tìm thấy đường đi trên GUI"""
        self.clear_path()
        self._no_path_text_item = QGraphicsTextItem("⚠️ NO PATH")
        self._no_path_text_item.setDefaultTextColor(QColor(255, 0, 0))
        self._no_path_text_item.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
        self._no_path_text_item.setPos(pos[0] + 10, pos[1] - 15)
        self.scene.addItem(self._no_path_text_item)

    def find_path(self, start_px, goal_name, ref_point=None):
        if goal_name not in self.all_nodes: 
            return None

        SNAP_THRESHOLD = 8.0
        
        # 1. LOGIC SNAP
        closest_node = min(self.all_nodes.keys(), key=lambda n: np.linalg.norm(np.array(start_px) - np.array(self.all_nodes[n])))
        min_dist = np.linalg.norm(np.array(start_px) - np.array(self.all_nodes[closest_node]))
        is_snapped = min_dist <= SNAP_THRESHOLD

        G = self.graph.copy()
        start_node = "START_VIRTUAL"

        if is_snapped:
            print(f"[STATUS] SNAPPED to Waypoint: '{closest_node}' (Dist: {min_dist:.2f}px)")
            start_node = closest_node
        else:
            print(f"[STATUS] Vị trí tự do (Dist tới {closest_node}: {min_dist:.2f}px)")
            candidates = self._get_candidates(start_px)
            for cand in candidates:
                dist_to_cand = np.linalg.norm(np.array(start_px) - np.array(self.all_nodes[cand]))
                G.add_edge(start_node, cand, weight=dist_to_cand)

        print(f"Goal: {goal_name}")

        try:
            # Tìm đường ngắn nhất
            path_node_names = nx.shortest_path(G, source=start_node, target=goal_name, weight='weight')
            
            # Nếu tìm được đường, xóa cảnh báo NO PATH cũ đi (nếu có)
            if self._no_path_text_item:
                try: self.scene.removeItem(self._no_path_text_item)
                except: pass
                self._no_path_text_item = None
            
            path_coords = [start_px]
            for name in path_node_names:
                if name == "START_VIRTUAL":
                    continue
                path_coords.append(self.all_nodes[name])

            self.draw_path(path_coords)
            printable_route = [n for n in path_node_names if n != "START_VIRTUAL"]
            print(f"Route tối ưu: {' -> '.join(printable_route)}")
            
            return path_coords

        except nx.NetworkXNoPath:
            print(f"Không có đường đi kết nối tới {goal_name}.")
            self._show_no_path_warning(start_px)
            return None
        except Exception as e:
            print(f"Lỗi thuật toán: {e}")
            self._show_no_path_warning(start_px)
            return None

    def _draw_fixed_points(self):
        for name, pos in self.waypoints.items():
            self._add_marker(pos[0], pos[1], name, QColor(0, 255, 0), 4)
        for name, pos in self.goals.items():
            self._add_marker(pos[0], pos[1], name, QColor(255, 200, 0), 6)

    def _add_marker(self, x, y, label, color, r):
        brush = QBrush(color)
        pen = QPen(Qt.GlobalColor.black, 1)
        ellipse = self.scene.addEllipse(x - r, y - r, r * 2, r * 2, pen, brush)
        ellipse.setZValue(50) 
        text = self.scene.addText(label)
        text.setPos(x + 10, y - 12)
        text.setDefaultTextColor(Qt.GlobalColor.black) 
        text.setZValue(51) 

    def draw_path(self, path):
        self.clear_path()
        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine)
        for i in range(len(path) - 1):
            line = self.scene.addLine(path[i][0], path[i][1], path[i+1][0], path[i+1][1], pen)
            line.setZValue(10)
            self.path_items.append(line)

    def clear_path(self):
        for item in self.path_items: 
            try: self.scene.removeItem(item)
            except: pass
        self.path_items.clear()
        
        if hasattr(self, '_no_path_text_item') and self._no_path_text_item is not None:
            try: self.scene.removeItem(self._no_path_text_item)
            except: pass
            self._no_path_text_item = None