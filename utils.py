import json
from math import radians, sin, cos, sqrt, atan2

import os
from typing import List, Tuple, Union


def parse_geojson(filename="Bonn Cycle Network.geojson"):
    """Parse the geojson file and return the data"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_path = os.path.join(script_dir, filename)

    try:
        with open(geojson_path) as file:
            geojson_data = json.load(file)
        return geojson_data
    except FileNotFoundError as e:
        print("Error:", str(e))
        return None


def distance(p1: Union[List, Tuple], p2: Union[List, Tuple]) -> float:
    """Calculate the distance between two points"""
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


# Get the category color based on properties
def get_category_color(properties, category_colors):
    """Get the category color based on properties"""
    if properties and properties.get("designated paths"):
        return category_colors.get("designated paths")  # Color for features shared with cars
    elif properties and properties.get("shared with pedestrian"):
        return category_colors.get("shared with pedestrian")  # Color for features with designated paths
    elif properties and properties.get("shared with cars"):
        return category_colors.get("shared with cars")  # Color for features shared with pedestrians
    else:
        return category_colors.get("No Infrastructure")  # Default color for other features
