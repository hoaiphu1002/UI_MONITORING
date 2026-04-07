import numpy as np
import networkx as nx
import json
import math
from datetime import datetime
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtCore import Qt

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

        SNAP_THRESHOLD = 8.0
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
                    if len(path_coords) >= 2 and 'wp4' in self.waypoints:
                        home_pt = np.array(self.all_nodes['Home'])
                        prev_pt = np.array(path_coords[-2])
                        wp4_pt = np.array(self.waypoints['wp4'])
                        angle_deg, signed = self._compute_angle_between(prev_pt, home_pt, wp4_pt)
                        self._draw_angle_visual(prev_pt, home_pt, wp4_pt, angle_deg, signed)
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