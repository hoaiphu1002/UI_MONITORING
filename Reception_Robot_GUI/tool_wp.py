import os, sys, json
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
import json
from MQTT.publisher_waypoints import WaypointsPublisher


tupple_x = [17.6858554792, 16.8749998552, 19.9679920085, 19.6681547578, 18.4091273325, 13.4507733824, 13.4117297827, 19.1596853144, 19.66815475, 19.96799200, 16.87499985, 17.68585547]
tupple_y = [1.52747189432,  12.4088992202, 14.4544250146, 20.8412712994, 26.2399740808, 26.0336352831, 24.3740114849, 24.5011076441, 20.84127129, 14.45442501, 12.4088992202, 1.527471894]

plan_points = []
for (x, y) in zip(tupple_x, tupple_y):
    plan_points.append({"x": x, "y": y})

waypoints_json = json.dumps(plan_points, indent=2)
print(f"Waypoints JSON:\n{waypoints_json}")
publisher = WaypointsPublisher()
publisher.publish_waypoints(waypoints_json)