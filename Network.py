import json
import os
import networkx as nx

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy.spatial.distance import cdist
import utm
from typing import List, Tuple, Union, Dict
from scipy.spatial import KDTree
from typing import List, Tuple, Dict
from utils import get_category_color, parse_geojson, distance


category_colors = {
    "shared with cars": "orange",
    "designated paths": "green",
    "shared with pedestrian": "blue",
    "No Infrastructure": "red",
}

surface_categories = {
    "asphalt": ["asphalt"],
    "compacted": ["compacted"],
    "loose and rough": [
        "fine_gravel",
        "gravel",
        "cobblestone",
        "hardpack",
        "hardwood",
        "pebblestone",
        "sett",
        "unpaved",
        "dirt",
        "dirt/sand",
        "earth",
        "ground",
        "metal",
        "sand",
        "soil",
        "stepping_stones",
        "wood",
    ],
    "paved": ["asphalt:lanes", "concrete", "concrete:plates", "paving_stones"],
}
surface_category_scores = {
    "asphalt": 0.8,
    "compacted": 0.95,
    "paved": 1.1,
    "loose and rough": 1.2,
}
default_surface_score = 1.4  # Score for other surface types

category_scores = {
    "designated paths": 0.2,  # Score for designated paths
    "shared with pedestrian": 0.4,  # Score for features shared with pedestrians
    "shared with cars": 0.75,  # Score for features shared with cars
    # Add more category scores as needed
}
default_category_score = 1  # Score for other categories


def find_nearest_node(graph: nx.Graph, target_node: Tuple) -> Tuple[Tuple, float]:
    if target_node in graph.nodes():
        target_node = graph.nodes[target_node]["utm_coord"]
        #print("Debug: target_node =", target_node)
    nodes_idx = graph.graph["kdTree"].query([target_node])
    node = list(graph.nodes())[nodes_idx[1][0]]
    return node, nodes_idx[0][0]


def get_surface_category(surface_type: str, surface_categories: Dict) -> str:
    for category, types in surface_categories.items():
        if surface_type in types:
            return category
    return "others"

def get_category_color(properties: Dict, category_colors: Dict) -> str:
    if properties.get("shared with cars", False):
        return "shared with cars"
    elif properties.get("designated paths", False):
        return "designated paths"
    elif properties.get("shared with pedestrian", False):
        return "shared with pedestrian"
    else:
        return "No Infrastructure"



def read_graph(alphaa: float = 1.0) -> nx.Graph:
    geojson_data = parse_geojson()
    graph = nx.Graph()
    for feature in geojson_data["features"]:
        if feature["geometry"]["type"] == "LineString":
            coordinates = feature["geometry"]["coordinates"]
            for current_coord in coordinates:
                utm_coord = utm.from_latlon(*current_coord[::-1])[:2]
                graph.add_node(tuple(current_coord), utm_coord=utm_coord)
    for feature in geojson_data["features"]:
        if feature["geometry"]["type"] == "LineString":
            coordinates = np.array(feature["geometry"]["coordinates"])
            properties = feature["properties"]
            category_color = get_category_color(properties, category_colors)
            surface = properties.get("surface")

            for i in range(len(coordinates) - 1):
                current_coord = tuple(coordinates[i])
                next_coord = tuple(coordinates[i + 1])

                dist = distance(graph.nodes[current_coord]["utm_coord"], graph.nodes[next_coord]["utm_coord"])
                surface_score = surface_category_scores.get(
                    get_surface_category(surface, surface_categories), default_surface_score
                )
                category_score = category_scores.get(category_color, default_category_score)
                weight = (1 - alphaa) * dist + alphaa * dist * surface_score * category_score

                graph.add_edge(current_coord, next_coord, distance=dist, category=category_color, weight=weight)

    largest_connected_component = max(nx.connected_components(graph), key=len)
    graph = graph.subgraph(largest_connected_component).copy()
    coords = [node[1]["utm_coord"] for node in graph.nodes(data=True)]
    graph.graph["kdTree"] = KDTree(coords)
    return graph


def calculate_shortest_safest_path(
    graph: nx.Graph, start_node: Tuple, end_node: Tuple) -> Tuple[List, float, nx.Graph]:
    total_length = 0
    additional_files = ["schools.geojson", "museums.geojson", "polizei.geojson"]
    additional_points = []

    for file in additional_files:
        if os.path.isfile(file):
            with open(file) as f:
                additional_data = json.load(f)

            for feature in additional_data["features"]:
                if feature["geometry"]["type"] == "Point":
                    coordinates = tuple(feature["geometry"]["coordinates"])
                    additional_points.append(coordinates)

    if start_node not in list(graph.nodes):
        start_node = find_nearest_node(graph, start_node)
    if end_node not in list(graph.nodes):
        end_node = find_nearest_node(graph, end_node)

    additional_start_nodes = [find_nearest_node(graph, poi_coord) for poi_coord in additional_points]

    try:
        shortest_path = nx.shortest_path(graph, start_node, end_node, weight="weight")

        if start_node in additional_points:
            start_index = additional_points.index(start_node)
            start_node = additional_start_nodes[start_index]
            shortest_path[0] = start_node
        if end_node in additional_points:
            end_index = additional_points.index(end_node)
            end_node = additional_start_nodes[end_index]
            shortest_path[-1] = end_node

        for i in range(len(shortest_path) - 1):
            current_coord = shortest_path[i]
            next_coord = shortest_path[i + 1]
            edge_data = graph.get_edge_data(current_coord, next_coord)
            total_length += (edge_data["distance"])/1000

        return shortest_path, total_length, graph

    except nx.NetworkXNoPath:
        return [], 0, graph
    

if __name__ == "__main__":
    # Example UTM coordinates for two points in Bonn, Germany (Zone 32T)
    start_node = (361750.487, 5620104.35012 ) # UTM coordinates for the starting point
    end_node =  (366342.797, 5621616.124) # UTM coordinates for the ending point
    """start_node = ( 366979.386, 5622397.348) # UTM coordinates for the starting point
    end_node =  (365719.553, 5622653.473) # UTM coordinates for the ending point"""

    # Example alphaa value (adjust as needed)
    alphaa = 1

    try:
        graph = read_graph(alphaa)

        # Find the nearest nodes in the graph
        start_node_utm, _ = find_nearest_node(graph, start_node)
        end_node_utm, _ = find_nearest_node(graph, end_node)

        # Calculate the shortest and safest path
        shortest_path, total_length, _ = calculate_shortest_safest_path(graph, start_node_utm, end_node_utm)

        if shortest_path:
            print("Total length:", total_length, "km")

            x_coords = [coord[1] for coord in shortest_path]
            y_coords = [coord[0] for coord in shortest_path]

            pos = nx.get_node_attributes(graph, "utm_coord")
            edges = graph.edges()

            # Extract edge categories from the GeoJSON properties
            edge_categories = [graph.get_edge_data(edge[0], edge[1])["category"] for edge in edges]

            # Assign colors based on edge categories
            edge_colors = [
                "orange" if category == "shared with cars" else
                "green" if category == "designated paths" else
                "blue" if category == "shared with pedestrian" else
                "red"  # for "No Infrastructure"
                for category in edge_categories
            ]

            # Draw edges for the entire graph with category colors
            nx.draw_networkx_edges(graph, pos, edgelist=edges, edge_color=edge_colors, width=1, alpha=0.5)

            # Draw the shortest path edges with a single color
            shortest_path_edges = list(zip(shortest_path, shortest_path[1:]))
            # Extract edge categories for the shortest path
            shortest_path_edge_categories = [graph.get_edge_data(edge[0], edge[1])["category"] for edge in shortest_path_edges]

            # Assign colors based on edge categories for the shortest path
            shortest_path_edge_colors = [
                "orange" if category == "shared with cars" else
                "green" if category == "designated paths" else
                "blue" if category == "shared with pedestrian" else
                "red"  # for "No Infrastructure"
                for category in shortest_path_edge_categories
            ]

            # Draw the shortest path edges with their respective category colors
            nx.draw_networkx_edges(graph, pos, edgelist=shortest_path_edges, edge_color=shortest_path_edge_colors, width=5, alpha=0.7)

            # Draw start and end nodes
            nx.draw_networkx_nodes(graph, pos, nodelist=[shortest_path[0]], node_size=100, node_color="green", label="Start Node")
            nx.draw_networkx_nodes(graph, pos, nodelist=[shortest_path[-1]], node_size=100, node_color="orange", label="End Node")

            # Create the legend handles
            legend_handles = [
                plt.Line2D([0], [0], color='orange', label='Shared with Cars'),
                plt.Line2D([0], [0], color='green', label='Designated Paths'),
                plt.Line2D([0], [0], color='blue', label='Shared with Pedestrian'),
                plt.Line2D([0], [0], color='red', label='No Infrastructure'),
                plt.Line2D([0], [0], marker='o', markersize=8, linestyle='None', color='green', label='Start Node'),
                plt.Line2D([0], [0], marker='o', markersize=8, linestyle='None', color='orange', label='End Node'),
            ]

            # Add the legend text
            legend_text = f'Total Length: {total_length:.2f} km\nα = {alphaa:.2f}'
            legend_handles.append(plt.Line2D([0], [0], color='white', label=legend_text))

            # Add the legend to the plot
            plt.legend(
                handles=legend_handles,
                loc='upper right',
                bbox_to_anchor=(1.0, 1.0),
            )

            # Add x and y axis labels
            plt.xlabel('X UTM Coordinate')
            plt.ylabel('Y UTM Coordinate')
            plt.axis("equal")
            plt.show()

        else:
            print("No path found between the start and end nodes.")

    except Exception as e:
        print("Error:", str(e))
