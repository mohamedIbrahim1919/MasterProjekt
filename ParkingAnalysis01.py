import sys
import traceback
import networkx as nx
import matplotlib.pyplot as plt
import utm  
from Network import calculate_shortest_safest_path, find_nearest_node,read_graph
from Parking import parse_parking_geojson
from utils import distance
from typing import List, Tuple, Union, Dict
from matplotlib.colors import ListedColormap

def add_parking_to_graph(graph: "nx.Graph", parking_nodes: List[Tuple]) -> None:
    """Add parking nodes to the graph"""
    for parking_node in parking_nodes:
        utm_coord = utm.from_latlon(*parking_node)[:2]  # Extract easting and northing
        print("Debug: utm_coord =", utm_coord)
        graph.add_node(tuple(utm_coord), category="Parking Node", utm_coord=utm_coord)
        graph_node, dist = find_nearest_node(graph, utm_coord)
        graph.add_edge(
            tuple(utm_coord),
            graph_node,
            category="Parking Node",
            distance=dist,
        )


def calculate_walking_distances(graph, end_node, parking_nodes):
    paths = nx.single_source_dijkstra_path(graph, end_node, weight='distance')
    walking_paths = {tuple(node): paths[node] for node in parking_nodes if tuple(node) in paths and isinstance(paths[tuple(node)][-1], (int, float))}
    walking_distances = {}
    for node, path in walking_paths.items():
        distance = 0
        for i in range(len(path) - 1):
            distance += graph[path[i]][path[i + 1]]["distance"]
        walking_distances[node] = distance
    return walking_paths, walking_distances



def calculate_bike_distances(graph, start_node, parking_nodes, alphaa):
    paths = nx.single_source_dijkstra_path(graph, start_node, weight='weight')
    bike_paths = {tuple(node): length * alphaa for node, length in paths.items() if tuple(node) in parking_nodes and isinstance(length, (int, float))}
    bike_distances = {}
    for node, path in bike_paths.items():
        distance = 0
        for i in range(len(path) - 1):
            distance += graph[path[i]][path[i + 1]]["distance"]
        bike_distances[node] = distance
    return bike_distances, bike_paths

def parking_analysis(start_node, end_node, alphaa, graph):
    parking_nodes = parse_parking_geojson()
    graph = read_graph(alphaa)
    add_parking_to_graph(graph, parking_nodes)
    #print("Graph nodes:", list(graph.nodes))


    try:
        nearest_start_node = find_nearest_node(graph, start_node), 0

        if start_node not in parking_nodes:
            start_bike_distances = calculate_bike_distances(graph, start_node, parking_nodes, alphaa)
            if not start_bike_distances:
                raise ValueError("Error: Bike distance could not be calculated for the start node.")
        else:
            start_bike_distances = {}

        if end_node not in parking_nodes:
            nearest_start_node, end_node = find_nearest_node(graph, nearest_start_node), find_nearest_node(graph, end_node)
            walking_distances, bike_distances = calculate_walking_distances(graph, end_node, parking_nodes), calculate_bike_distances(graph, nearest_start_node, parking_nodes, alphaa)

            if not walking_distances or not bike_distances:
                raise ValueError("Error: Walking or bike distances could not be calculated.")
                
            min_distance_parking_node = min(parking_nodes, key=lambda node: walking_distances[node] + bike_distances[node])
            total_distance = walking_distances[min_distance_parking_node] + bike_distances[min_distance_parking_node]
        else:
            walking_distance, total_distance = 0, 0

        print("Total Distance:", total_distance, "km")
        return [nearest_start_node] + ([min_distance_parking_node] if min_distance_parking_node else []) + [end_node], total_distance, graph

    except Exception as e:
        encoded_error = str(e).encode(sys.stdout.encoding, errors='replace')
        print("Error:", encoded_error.decode(sys.stdout.encoding))
        return None, 0, graph


if __name__ == "__main__":
    start_node = (366284.56132444367, 5619604.967375053)
    end_node = (365520.083927908, 5620743.976031874)
    alphaa = 1

    graph = read_graph(alphaa)
    #print("Graph nodes:", list(graph.nodes))
    parking_nodes = parse_parking_geojson()
    #print("parking Nodes: ", parking_nodes)
    #print("number of parking nodes: ", len(parking_nodes))
    add_parking_to_graph(graph, parking_nodes)


    try:
        path, total_distance, graph = parking_analysis(start_node, end_node, alphaa, graph)
        walking_paths,walking_distances = calculate_walking_distances(graph, end_node, parking_nodes)
        bike_paths,bike_distances = calculate_bike_distances(graph, start_node, parking_nodes, alphaa)

        if path and walking_distances and bike_distances:
            print("Total length:", total_distance, "meters")

        if path and total_distance:
            print("Total length:", total_distance, "meters")

            x_coords = [coord[1] for coord in path]
            y_coords = [coord[0] for coord in path]

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

            # Print total walking distance
            total_walking_distance = sum(walking_distances.values())
            print("\nTotal Walking Distance:", total_walking_distance, "meters")

            # Print total bike distance
            total_bike_distance = sum(bike_distances.values())
            print("Total Bike Distance:", total_bike_distance, "meters")

        else:
            print("No path found between the start and end nodes.")

    except Exception as e:
        print("Error:", str(e))
