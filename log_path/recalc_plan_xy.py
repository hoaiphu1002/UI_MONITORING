import csv
import numpy as np

# Danh sách waypoint bạn gửi
waypoints = [
    # {"x": -0.06, "y": -0.054},
    # {"x": -0.06, "y": -0.054},
    # {"x": -0.06, "y": -0.054},
    # {"x": 4.39, "y": 0.446},
    # {"x": 14.69, "y": 0.746},
    # {"x": 30.99, "y": 1.746},
    # {"x": 37.04, "y": 1.846},
    # {"x": 40.74, "y": 1.796},
    # {"x": 41.09, "y": 0.346}
  {
    "x": -0.06,
    "y": -0.054
  },
  {
    "x": -0.06,
    "y": -0.054
  },
  {
    "x": -0.06,
    "y": -0.054
  },
  {
    "x": 4.39,
    "y": 0.446
  },
  {
    "x": 4.34,
    "y": 1.446
  },
  {
    "x": 3.94,
    "y": 4.946
  },
  {
    "x": 3.79,
    "y": 9.296
  },
  {
    "x": 3.59,
    "y": 13.946
  },
  {
    "x": 7.14,
    "y": 15.396
  },
  {
    "x": 15.04,
    "y": 15.346
  },
  {
    "x": 25.39,
    "y": 16.146
  }
]
waypoints = [(wp["x"], wp["y"]) for wp in waypoints]

def project_point_to_segment(x1, y1, x2, y2, xr, yr):
    vx, vy = x2 - x1, y2 - y1
    wx, wy = xr - x1, yr - y1
    c1 = wx * vx + wy * vy
    c2 = vx * vx + vy * vy
    if c2 == 0:
        t = 0.0
    else:
        t = max(0.0, min(1.0, c1 / c2))
    plan_x = x1 + t * vx
    plan_y = y1 + t * vy
    return plan_x, plan_y

# Đọc file log
log_path = "log_path/path_comparison_B2_14_4.csv"
out_path = "log_path/path_comparison_B2_14_4_recalc.csv"

with open(log_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    data = [row for row in reader if row and row[0][0].isdigit()]

fixed_rows = []
seg_idx = 0
for row in data:
    actual_x = float(row[1])
    actual_y = float(row[2])
    # Tìm đoạn phù hợp
    while seg_idx + 1 < len(waypoints):
        x1, y1 = waypoints[seg_idx]
        x2, y2 = waypoints[seg_idx + 1]
        dist_to_next = np.hypot(actual_x - x2, actual_y - y2)
        if dist_to_next < 0.5 and seg_idx + 2 < len(waypoints):
            seg_idx += 1
        else:
            break
    # Nếu đã hết waypoint thì giữ đoạn cuối
    if seg_idx + 1 >= len(waypoints):
        x1, y1 = waypoints[-2]
        x2, y2 = waypoints[-1]
    plan_x, plan_y = project_point_to_segment(x1, y1, x2, y2, actual_x, actual_y)
    error = np.hypot(actual_x - plan_x, actual_y - plan_y)
    fixed_rows.append([
        row[0],  # time
        f'{actual_x:.3f}',
        f'{actual_y:.3f}',
        f'{plan_x:.3f}',
        f'{plan_y:.3f}',
        f'{error:.3f}'
    ])

with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['time', 'actual_x', 'actual_y', 'plan_x', 'plan_y', 'error_m'])
    writer.writerows(fixed_rows)

print(f"Đã xuất file mới: {out_path}")
