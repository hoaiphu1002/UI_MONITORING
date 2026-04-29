import numpy as np
import networkx as nx
import json
import math
from datetime import datetime
from PyQt6.QtGui import QPen, QColor, QBrush, QPainterPath
from PyQt6.QtCore import Qt
import os, sys
# ensure project root is on sys.path so `MQTT` package can be imported when running file directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from MQTT.publisher_angle import AnglePublisher
from MQTT.mqtt_publisher_config import get_topic
from datetime import datetime as _dt

class PathPlanner:
    def __init__(self, scene, config_path="Reception_Robot_GUI/resources/Map/B1_config_wp.json"):
        self.scene = scene
        self.path_items = []
        self.angle_items = []
        
        # Load dữ liệu từ JSON
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        self.waypoints = config['waypoints']
        self.goals = config['goals']
        self.connections = config['connections']
        
        # Hợp nhất tất cả các điểm
        self.all_nodes = {**self.waypoints, **self.goals}
        
        # --- THIẾT LẬP HỆ SỐ PHẠT ---
        self.BASE_TURN_PENALTY = 5000.0
        self.SHARP_TURN_MULTIPLIER = 100.0
        
        # Xây dựng Đồ thị góc rẽ (Turn Graph) ngay từ lúc khởi tạo
        self._build_static_turn_graph()
        self._draw_fixed_points()
        # Lazy angle publisher (created on first use)
        self._angle_publisher = None

    def _build_static_turn_graph(self):
        """Xây dựng Line Graph: Các nút là các cạnh có hướng (u, v)"""
        self.static_turn_graph = nx.DiGraph()
        
        for v in self.connections:
            for u in self.connections: # Giả định đồ thị có thể đi 2 chiều nếu bạn khai báo cả 2
                if v in self.connections.get(u, []):
                    # Đây là một cạnh có hướng (u -> v)
                    edge_in = (u, v)
                    
                    # Tìm các cạnh tiếp theo (v -> w)
                    for w in self.connections.get(v, []):
                        if w == u: continue # Bỏ qua quay đầu tại chỗ 180 độ trên cùng 1 cạnh
                        
                        edge_out = (v, w)
                        
                        # Tính khoảng cách thực đoạn v -> w
                        dist_v_w = np.linalg.norm(np.array(self.all_nodes[v]) - np.array(self.all_nodes[w]))
                        
                        # Tính Penalty góc rẽ tại v khi đi từ u -> v -> w
                        v1 = np.array(self.all_nodes[v]) - np.array(self.all_nodes[u])
                        v2 = np.array(self.all_nodes[w]) - np.array(self.all_nodes[v])
                        penalty = self._calculate_penalty_from_vectors(v1, v2)
                        
                        # Thêm vào đồ thị rẽ: Trọng số = Quãng đường + Hình phạt quẹo
                        self.static_turn_graph.add_edge(edge_in, edge_out, weight=dist_v_w + penalty)

    def _calculate_penalty_from_vectors(self, v1, v2):
        """Tính penalty giữa 2 vector hướng"""
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6: return 0
        
        dot = np.clip(np.dot(v1/norm1, v2/norm2), -1.0, 1.0)
        angle_diff = math.acos(dot)
        
        if angle_diff > math.pi / 2 + 0.1: # Góc quẹo > 90 (Góc nội bộ nhọn)
            return self.BASE_TURN_PENALTY * (angle_diff / math.pi) * self.SHARP_TURN_MULTIPLIER
        return self.BASE_TURN_PENALTY * (angle_diff / math.pi)

    def find_path(self, start_px, goal_name, ref_point=None):
        if goal_name not in self.all_nodes: return None

        SNAP_THRESHOLD = 15.0
        # 1. LOGIC SNAP
        closest_node = min(self.all_nodes.keys(), key=lambda n: np.linalg.norm(np.array(start_px) - np.array(self.all_nodes[n])))
        min_dist = np.linalg.norm(np.array(start_px) - np.array(self.all_nodes[closest_node]))
        is_snapped = min_dist <= SNAP_THRESHOLD

        # Tạo bản sao đồ thị rẽ để thêm các nút ảo START/END cho lượt này
        G = self.static_turn_graph.copy()
        start_node_virtual = "START_VIRTUAL"
        end_node_virtual = "END_VIRTUAL"

        # 2. Vector hướng hiện tại
        v_heading = None
        if ref_point is not None:
            v_heading = np.array(start_px) - np.array(ref_point)
            if np.linalg.norm(v_heading) < 1.0: v_heading = None

        # 3. Kết nối START_VIRTUAL vào các cạnh bắt đầu khả thi
        start_points = [closest_node] if is_snapped else self._get_candidates(start_px)
        for sp in start_points:
            for nb in self.connections.get(sp, []):
                # Nút trong turn_graph là (sp, nb)
                target_edge_node = (sp, nb)
                dist_robot_to_sp = np.linalg.norm(np.array(start_px) - np.array(self.all_nodes[sp]))
                
                # Penalty rẽ ngay từ hướng robot vào cạnh sp->nb
                v_first_edge = np.array(self.all_nodes[nb]) - np.array(self.all_nodes[sp])
                p_init = self._calculate_penalty_from_vectors(v_heading, v_first_edge) if v_heading is not None else 0
                
                # Trọng số cạnh ảo = đường đến điểm đầu + phạt rẽ + đường đoạn đầu sp-nb
                # Lưu ý: Ta cộng luôn dist sp-nb vì nút tiếp theo trong DiGraph sẽ bắt đầu tính từ nb
                dist_sp_nb = np.linalg.norm(np.array(self.all_nodes[sp]) - np.array(self.all_nodes[nb]))
                G.add_edge(start_node_virtual, target_edge_node, weight=dist_robot_to_sp + p_init + dist_sp_nb)

        # 4. Kết nối các cạnh dẫn tới ĐÍCH vào END_VIRTUAL
        for u in self.all_nodes:
            if goal_name in self.connections.get(u, []):
                # Nếu có cạnh u -> goal_name, nối nó vào nút kết thúc ảo
                G.add_edge((u, goal_name), end_node_virtual, weight=0)

        # 5. Dijkstra trên Turn Graph
        if is_snapped:
            print(f"[STATUS] SNAPPED to Waypoint: '{closest_node}' (Dist: {min_dist:.2f}px)")
        else:
            print(f"[STATUS] Vị trí tự do (Dist tới {closest_node}: {min_dist:.2f}px)")
        
        print(f"Goal: {goal_name}")

        try:
            # Kết quả là danh sách các CẠNH: [START, (u,v), (v,w), ..., END]
            best_path_edges = nx.shortest_path(G, source=start_node_virtual, target=end_node_virtual, weight='weight')
            
            # Chuyển đổi list cạnh thành list tọa độ điểm
            path_coords = [start_px]
            path_node_names = []
            
            for edge in best_path_edges:
                if isinstance(edge, tuple): # Bỏ qua START_VIRTUAL và END_VIRTUAL
                    u, v = edge
                    if not path_node_names or path_node_names[-1] != u:
                        path_node_names.append(u)
                    if v not in path_node_names:
                        path_node_names.append(v)

            # Lấy tọa độ từ tên node
            for name in path_node_names:
                path_coords.append(self.all_nodes[name])

            self.draw_path(path_coords)
            # Nếu đích là Home thì tính góc lệch so với waypoint tham chiếu (wp4)
            try:
                if goal_name == 'Home':
                    # Last coord is Home
                    # Nếu có waypoint tham chiếu `wp14`, tính góc lệch giữa vector vào Home (prev -> Home)
                    # và vector từ Home tới wp14 (Home -> wp14)
                    if len(path_coords) >= 2 and 'wp14' in self.waypoints:
                        home_pt = np.array(self.all_nodes['Home'])
                        prev_pt = np.array(path_coords[-2])
                        wp14_pt = np.array(self.waypoints['wp14'])
                        angle_deg, signed, dot = self._compute_angle_between(prev_pt, home_pt, wp14_pt)
                        # save for external access
                        self.last_deviation_angle = angle_deg
                        self.last_deviation_sign = signed
                        self.last_deviation_signed_angle = signed * angle_deg
                        self.last_deviation_angle_360 = (self.last_deviation_signed_angle + 360.0) % 360.0
                        self.last_deviation_dot = dot
                        self._draw_angle_visual(prev_pt, home_pt, wp14_pt, angle_deg, signed)
                        # Do not publish here: this angle is path-predicted, not real robot heading at arrival.
            except Exception as ex:
                print(f"Error computing/drawing angle: {ex}")
            print(f"Route tối ưu: {' -> '.join(path_node_names)}")
            return path_coords

        except Exception as e:
            print(f"Không tìm thấy đường đi mượt, đi thẳng. Lỗi: {e}")
            path = [start_px, self.all_nodes[goal_name]]
            self.draw_path(path)
            return path

    # --- Các hàm hỗ trợ vẽ và marker giữ nguyên ---
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

    def _get_candidates(self, point):
        dist_to_point = lambda name: np.linalg.norm(np.array(point) - np.array(self.all_nodes[name]))
        candidates = sorted(self.all_nodes.keys(), key=dist_to_point)
        return candidates[:3] 

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
        # also clear angle visuals when clearing path
        for item in self.angle_items:
            try: self.scene.removeItem(item)
            except: pass
        self.angle_items.clear()

    def _compute_angle_between(self, prev_pt, home_pt, ref_pt):
        """Compute angle between two vectors and return (angle_deg, sign, dot).

        Vectors used:
        - incoming: prev_pt -> home_pt
        - reference: home_pt -> ref_pt

        Returns tuple: (angle_deg, sign, dot_product)
        where sign is +1 for CCW, -1 for CW, and dot_product = v_in . v_ref.
        """
        v_in = np.array(home_pt) - np.array(prev_pt)
        v_ref = np.array(ref_pt) - np.array(home_pt)
        n1 = np.linalg.norm(v_in)
        n2 = np.linalg.norm(v_ref)
        if n1 < 1e-6 or n2 < 1e-6:
            return 0.0, 0, 0.0

        # raw dot and cosine
        dot_raw = float(np.dot(v_in, v_ref))
        cos_val = np.clip(dot_raw / (n1 * n2), -1.0, 1.0)
        angle_rad = math.acos(cos_val)
        angle_deg = math.degrees(angle_rad)

        # signed via 2D cross product z-component
        u1 = v_in / n1
        u2 = v_ref / n2
        cross_z = u1[0] * u2[1] - u1[1] * u2[0]
        sign = 1 if cross_z >= 0 else -1
        return angle_deg, sign, dot_raw

    def _draw_angle_visual(self, prev_pt, home_pt, ref_pt, angle_deg, sign):
        """Draw incoming vector, reference vector and an arc indicating the angle."""
        # clear previous
        for it in self.angle_items:
            try: self.scene.removeItem(it)
            except: pass
        self.angle_items.clear()

        hx, hy = float(home_pt[0]), float(home_pt[1])
        px, py = float(prev_pt[0]), float(prev_pt[1])
        rx, ry = float(ref_pt[0]), float(ref_pt[1])

        # Draw incoming line (prev -> home)
        pen_in = QPen(QColor(0, 100, 255), 2)
        line_in = self.scene.addLine(px, py, hx, hy, pen_in)
        line_in.setZValue(20)
        self.angle_items.append(line_in)

        # Draw reference line (home -> ref)
        pen_ref = QPen(QColor(0, 200, 0), 2)
        line_ref = self.scene.addLine(hx, hy, rx, ry, pen_ref)
        line_ref.setZValue(20)
        self.angle_items.append(line_ref)

        # Draw arc approximating the angle
        v1 = np.array([px - hx, py - hy]) * -1.0  # home->prev (incoming direction)
        v2 = np.array([rx - hx, ry - hy])
        a1 = math.atan2(v1[1], v1[0])
        a2 = math.atan2(v2[1], v2[0])

        # normalize delta to [-pi, pi]
        delta = a2 - a1
        while delta <= -math.pi: delta += 2 * math.pi
        while delta > math.pi: delta -= 2 * math.pi

        # choose radius for arc (small, visible)
        r = min(80.0, max(20.0, np.linalg.norm(v1) * 0.5, np.linalg.norm(v2) * 0.5))
        steps = 24
        path = QPainterPath()
        for i in range(steps):
            t = i / (steps - 1)
            theta = a1 + t * delta
            x = hx + r * math.cos(theta)
            y = hy + r * math.sin(theta)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        pen_arc = QPen(QColor(200, 0, 0), 2)
        arc_item = self.scene.addPath(path, pen_arc)
        arc_item.setZValue(21)
        self.angle_items.append(arc_item)

        # Angle label at midpoint of arc
        mid_theta = a1 + 0.5 * delta
        lx = hx + (r + 10) * math.cos(mid_theta)
        ly = hy + (r + 10) * math.sin(mid_theta)
        signed_angle = sign * angle_deg
        normalized_angle = (signed_angle + 360.0) % 360.0
        # UI uses normalized angle first, while still showing legacy signed angle.
        text = self.scene.addText(f"{normalized_angle:.1f}° (0-360)\n{signed_angle:.1f}° (signed)")
        text.setDefaultTextColor(Qt.GlobalColor.red)
        text.setPos(lx, ly)
        text.setZValue(30)
        self.angle_items.append(text)