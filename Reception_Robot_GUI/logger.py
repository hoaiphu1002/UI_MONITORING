import csv
import numpy as np
from datetime import datetime
import time
import pandas as pd
import math
import json
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class PathLogger(QObject):
    """
    Class chịu trách nhiệm ghi log path-comparison, xuất CSV và ghi vào plot 
    """
    cte_signal = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.location_tab = None
        self.log_data = []
        self.current_segment_idx = 0
        self.threshold_to_next = 0.3
        self.last_log_time = 0
        self.logging_active = False

    def start_logging(self, full_plan_points):
        """Gọi từ LocationTab.plan_path()"""
        self.full_plan_points = full_plan_points

        # Reset lại toàn bộ trạng thái – đúng như code gốc làm trong plan_path
        self.log_data = []
        self.current_segment_idx = 0
        self.last_log_time = 0
        self.logging_active = True

        # Tạo timer mới mỗi lần start (giống hệt code gốc)
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.logging_step)
        self.log_timer.start(100)  # 10 Hz check

    def logging_step(self):
        if not self.logging_active or len(self.full_plan_points) < 2:
            return

        now = time.time()
        if now - self.last_log_time < 1.0:
            return
        self.last_log_time = now

        actual_x = self.location_tab.last_position[0]
        actual_y = self.location_tab.last_position[1]
        timestamp = datetime.now()

        # Lấy đoạn hiện tại
        idx = self.current_segment_idx
        if idx + 1 >= len(self.full_plan_points):
            self.stop_logging()
            return

        p1 = self.full_plan_points[idx]
        p2 = self.full_plan_points[idx + 1]
        x1, y1 = p1["x"], p1["y"]
        x2, y2 = p2["x"], p2["y"]
        xr, yr = actual_x, actual_y

        # Vector
        vx, vy = x2 - x1, y2 - y1
        wx, wy = xr - x1, yr - y1
        c1 = wx * vx + wy * vy
        c2 = vx * vx + vy * vy

        if c2 == 0:
            t_raw = 0.0
        else:
            t_raw = c1 / c2
        t = max(0.0, min(1.0, t_raw)) # t between 0 and 1

        # Điểm chiếu lên đoạn thẳng
        plan_x = x1 + t * vx
        plan_y = y1 + t * vy

        # CTE
        error = np.hypot(xr - plan_x, yr - plan_y)
        self.cte_signal.emit(error)

        # Ghi log
        self.log_data.append((timestamp, plan_x, plan_y, actual_x, actual_y, error))

        # Kiểm tra chuyển đoạn
        dist_to_next = np.hypot(xr - x2, yr - y2)
        # pass next wp or close enough to next wp, move to next segment
        if (t_raw >= 1.0 or dist_to_next < self.threshold_to_next):
            if self.current_segment_idx + 2 < len(self.full_plan_points):
                self.current_segment_idx += 1

    def stop_logging(self):
        if hasattr(self, 'log_timer') and self.log_timer.isActive():
            self.log_timer.stop()
        self.logging_active = False
        self.export_path_comparison()

    def export_path_comparison(self):
        if not hasattr(self, 'log_data') or len(self.log_data) == 0:
            print("Robot is not moving")
            return
        if not hasattr(self, 'full_plan_points') or len(self.full_plan_points) < 2:
            print("No planned path")
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path = f"log_path/path_comparison_{timestamp_str}.csv"

        errors = [row[5] for row in self.log_data]

        with open(full_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'actual_x', 'actual_y', 'plan_x', 'plan_y', 'error_m'])
            for row in self.log_data:
                writer.writerow([
                    row[0].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    round(row[3], 3),
                    round(row[4], 3),
                    round(row[1], 3),
                    round(row[2], 3),
                    round(row[5], 3)
                ])
            writer.writerow([])
            if errors:
                mean_error = np.mean(errors)
                max_error = np.max(errors)
                summary = f"Avg error: {mean_error:.3f}m | Max error: {max_error:.3f}m"
                writer.writerow([summary])

        print(f"Exported: {full_path}")

        # Reset lại như code gốc
        self.log_data = []
        self.current_segment_idx = 0
        self.logging_active = False


def get_closest_projection(rx, ry, wps_array):
    min_error = float('inf')
    best_px, best_py = rx, ry
    
    for i in range(len(wps_array) - 1):
        x1, y1 = wps_array[i]
        x2, y2 = wps_array[i+1]
        
        vx, vy = x2 - x1, y2 - y1
        wx, wy = rx - x1, ry - y1
        
        c1 = wx * vx + wy * vy
        c2 = vx * vx + vy * vy
        
        if c2 == 0:
            t = 0.0
        else:
            t = max(0.0, min(1.0, c1 / c2))
            
        px = x1 + t * vx
        py = y1 + t * vy
        
        dist = math.hypot(rx - px, ry - py)
        
        if dist < min_error:
            min_error = dist
            best_px = px
            best_py = py
            
    return pd.Series([round(best_px, 3), round(best_py, 3), round(min_error, 3)])


def salvage_log_data(input_csv, output_csv, path_json):
    try:
        with open(path_json, 'r', encoding='utf-8') as f:
            wps_data = json.load(f)
            
        wps_array = [[point['x'], point['y']] for point in wps_data]
        
    except Exception as e:
        print(f"[ERROR] Cannot read file path JSON: {e}")
        return

    df_log = pd.read_csv(input_csv)
    
    df_log = df_log[~df_log['time'].astype(str).str.contains("Avg error|Max error", case=False, na=False)]
    
    df_log['actual_x'] = pd.to_numeric(df_log['actual_x'], errors='coerce')
    df_log['actual_y'] = pd.to_numeric(df_log['actual_y'], errors='coerce')
    
    df_log = df_log.dropna(subset=['actual_x', 'actual_y'])

    df_log[['plan_x', 'plan_y', 'error_m']] = df_log.apply(
        lambda row: get_closest_projection(row['actual_x'], row['actual_y'], wps_array), 
        axis=1
    )
    
    df_log.to_csv(output_csv, index=False)
    
    mean_err = df_log['error_m'].mean()
    max_err = df_log['error_m'].max()

    summary = f"Avg error: {mean_err:.3f}m | Max error: {max_err:.3f}m"

    with open(output_csv, 'a', encoding='utf-8') as f:
        f.write("\n")         
        f.write(summary + "\n") 
    
    print(f"[SUCCESS] File saved: {output_csv}")
    print(summary)

if __name__ == "__main__":
    input_file = "log_path/path_comparison_B2_14_4.csv"        
    output_file = "log_path/path_comparison_B2_14_4_fixed.csv" 
    path_file = "log_path/waypoints.json"
    salvage_log_data(input_file, output_file, path_file)