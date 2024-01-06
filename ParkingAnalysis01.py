import sys
import traceback
import networkx as nx
import matplotlib.pyplot as plt
import utm  
from Network import calculate_shortest_safest_path, find_nearest_node, read_graph
from Parking import parse_parking_geojson
from utils import distance
from typing import List, Tuple, Union, Dict
from matplotlib.colors import ListedColormap

def add_parking_to_graph(graph: "nx.Graph", parking_nodes: List[Tuple]) -> None:
    """Add parking nodes to the graph"""
    for parking_node in parking_nodes:
        utm_coord = utm.from_latlon(*parking_node[::-1])[:2]
        graph.add_node(parking_node, category="Parking Node", utm_coord=utm_coord)
        graph_node, dist = find_nearest_node(graph, utm_coord)
        graph.add_edge(
            parking_node,
            graph_node,
            category="Parking Node",
            distance=dist,
        )

def calculate_walking_distances(graph, end_node, parking_nodes):
    paths = nx.single_source_dijkstra_path(graph, end_node, weight='distance')
    walking_paths = {tuple(node): paths[node] for node in parking_nodes if tuple(node) in paths and isinstance(paths[tuple(node)][-1], (int, float))}
    #print("walking Path: ", walking_paths)
    walking_distances = {}
    for node, path in walking_paths.items():
        distance = 0
        for i in range(len(path) - 1):
            distance += graph[path[i]][path[i + 1]]["distance"]
        walking_distances[node] = (distance, path)
    return walking_paths, walking_distances

def calculate_bike_distances(graph, start_node, parking_nodes, alphaa):
    paths = nx.single_source_dijkstra_path(graph, start_node, weight='weight')
    #print("bike paths: ", paths)
    bike_paths = {tuple(node): path for node, path in paths.items() if tuple(node) in parking_nodes and isinstance(path, list)}
    #print("bike Path: ", bike_paths)
    bike_distances = {}
    for node, path in bike_paths.items():
        distance = 0
        for i in range(len(path) - 1):
            distance += graph[path[i]][path[i + 1]]["distance"]
        bike_distances[node] = (distance, path)
    return bike_distances, bike_paths

def parking_analysis(start_node, end_node, alphaa, graph):
    parking_nodes = parse_parking_geojson()
    graph = read_graph(alphaa)
    add_parking_to_graph(graph, parking_nodes)

    min_distance_parking_node = end_node
    total_distance = 0

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

            if min_distance_parking_node in walking_distances and min_distance_parking_node in bike_distances:
                total_distance = walking_distances[min_distance_parking_node][0] + bike_distances[min_distance_parking_node][0]
            else:
                total_distance = bike_distances[min_distance_parking_node][0]

        return [nearest_start_node] + [min_distance_parking_node] + [end_node], total_distance, graph

    except Exception as e:
        encoded_error = str(e).encode(sys.stdout.encoding, errors='replace')
        print("Error:", encoded_error.decode(sys.stdout.encoding))
        return None, 0, graph

def main():
    try:
        start_node = (7.095775, 50.7373406)
        end_node = (7.0881976166, 50.7213184826)
        alpha_value = 1

        # Load the graph and parking nodes
        graph = read_graph(alpha_value)
        parking_nodes = parse_parking_geojson()
        add_parking_to_graph(graph, parking_nodes)

        # Perform parking analysis
        path, total_distance, graph = parking_analysis(start_node, end_node, alpha_value, graph)
        bike_distances, _ = calculate_bike_distances(graph, start_node, parking_nodes, alpha_value)
        walking_distances, _ = calculate_walking_distances(graph, end_node, parking_nodes)

        if path is not None:
            if end_node in parking_nodes:
                # If the end node is a parking node, set min_distance_parking_node to end_node
                min_distance_parking_node = end_node
                walking_distances[min_distance_parking_node] = 0
                total_distance = (bike_distances[min_distance_parking_node][0])/1000    
            else:
                min_distance_parking_node = min(parking_nodes, key=lambda node: walking_distances[node] + bike_distances[node])

            print("min park node:", min_distance_parking_node)
            print("walking distance:", (walking_distances[min_distance_parking_node])/1000,"km")
            print("bike distance:", (bike_distances[min_distance_parking_node][0])/1000,"km")
            print("Bike path :", bike_distances[min_distance_parking_node][1])
            # Print the total distance
            print("Total distance:", total_distance)

        else:
            print("Analysis failed.")

    except Exception as e:
        print("An error occurred:", str(e))

if __name__ == "__main__":
    main()
