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
import contextily as ctx  # Import contextily library
import geopandas as gpd


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
        
    walking_paths = nx.single_source_dijkstra_path(graph, end_node, weight='weight')
    #print("walk paths: ", paths)
    #print("walking_paths: ", walking_paths)
    walking_distances = {}
    for node, path in walking_paths.items():
        distance = 0
        for i in range(len(path) - 1):
            distance += graph[path[i]][path[i + 1]]["distance"]
        walking_distances[node] = distance
    return walking_paths, walking_distances

def calculate_bike_distances(graph, start_node, parking_nodes, alphaa):
    bike_paths = nx.single_source_dijkstra_path(graph, start_node, weight='weight')
    #print("bike paths: ", paths)
    #print("bike Path: ", bike_paths)
    bike_distances = {}
    for node, path in bike_paths.items():
        distance = 0
        for i in range(len(path) - 1):
            distance += graph[path[i]][path[i + 1]]["distance"]
        bike_distances[node] = distance
    return bike_paths, bike_distances

def parking_analysis(start_node, end_node, alphaa, graph):
    parking_nodes = parse_parking_geojson()
    graph = read_graph(alphaa)
    add_parking_to_graph(graph, parking_nodes)

    nearest_start_node, start_distance = find_nearest_node(graph, start_node)
    nearest_end_node, end_distance = find_nearest_node(graph, end_node)

    bike_paths, bike_distances = calculate_bike_distances(graph, nearest_start_node, parking_nodes, alphaa)
    walking_paths, walking_distances = calculate_walking_distances(graph, nearest_end_node, parking_nodes)

    total_distances = [walking_distances[node] + bike_distances[node] for node in parking_nodes]
    min_distance = min(total_distances)
    idx_min = total_distances.index(min_distance)
    min_distance_parking_node = parking_nodes[idx_min]

    total_distance = total_distances[idx_min]
    bike_distance = bike_distances[min_distance_parking_node]
    walking_distance = walking_distances[min_distance_parking_node]

    # Extract bike and walking paths
    bike_path_start_to_parking = bike_paths[min_distance_parking_node]
    walking_path_parking_to_end = walking_paths[min_distance_parking_node]

    return (
        [nearest_start_node] + [min_distance_parking_node] + [end_node],
        total_distance,
        bike_distance,
        walking_distance,
        graph,
        bike_path_start_to_parking,
        walking_path_parking_to_end,
        min_distance_parking_node,
    )


def main():
    
        start_node = (7.1071226, 50.7319471)
        end_node = (7.0931056, 50.7264752)
        alpha_value = 1

        # Load the graph and parking nodes
        graph = read_graph(alpha_value)
        parking_nodes = parse_parking_geojson()
        add_parking_to_graph(graph, parking_nodes)
        
        # Perform parking analysis
        path, total_distance, bike_distance, walking_distance, graph, bike_path_start_to_parking, walking_path_parking_to_node, min_distance_parking_node  = parking_analysis(start_node, end_node, alpha_value, graph)
        
        # Nearest node to start node
        nearest_start_node, _ = find_nearest_node(graph, start_node)
        print("nearest start node:" , nearest_start_node)

        # Nearest node to end node
        nearest_end_node, _ = find_nearest_node(graph, end_node)
        print("nearest end node:", nearest_end_node)

        #print("walking path: ", walking_path_parking_to_node)
        #print("bike path: ", bike_path_start_to_parking)
        #print("min park node:", path[1])
        print("walking distance:", walking_distance/1000,"km")
        print("bike distance:", bike_distance/1000,"km")
        # Print the total distance
        print("Total distance:", total_distance/1000, "km")


        # Plot the graph using UTM coordinates
        pos = nx.get_node_attributes(graph, "utm_coord")
        edges = graph.edges()

        # Extract edge categories from the GeoJSON properties
        edge_categories = [graph.get_edge_data(edge[0], edge[1])["category"] for edge in edges]
        
        # Convert coordinates to edges for bike path
        bike_path_edges = [(bike_path_start_to_parking[i], bike_path_start_to_parking[i+1]) for i in range(len(bike_path_start_to_parking)-1)]
        #print("bike path edges: ", bike_path_edges)

        # Convert coordinates to edges for walking path
        walking_path_edges = [(walking_path_parking_to_node[i], walking_path_parking_to_node[i+1]) for i in range(len(walking_path_parking_to_node)-1)]
        #print("walking path edges: ", walking_path_edges)

        # Assign colors based on edge categories
        edge_colors = [
            "orange" if category == "shared with cars" else
            "green" if category == "designated paths" else
            "blue" if category == "shared with pedestrian" else
            "red"  # for "No Infrastructure"
            for category in edge_categories
        ]
        # Plot the graph using UTM coordinates
        fig, ax = plt.subplots()
        # Draw edges for the entire graph with category colors
        nx.draw_networkx_edges(graph, pos, edgelist=edges, edge_color='gray', width=3, alpha=0.8, label="Road Network")

        # Draw the walking path to the node with a specific color
        nx.draw_networkx_edges(graph, pos, edgelist=walking_path_edges, edge_color='green', width=5, label="Walking Path")

        # Draw the bike path to the parking with a specific color
        nx.draw_networkx_edges(graph, pos, edgelist=bike_path_edges, edge_color='blue', width=5, label="Bike Path")
        # Draw all parking nodes in blue
        nx.draw_networkx_nodes(graph, pos, nodelist=parking_nodes, node_color='blue', node_size=20, label="Parking Nodes")


        nx.draw_networkx_nodes(graph, pos, nodelist=[nearest_start_node], node_color='green', node_size=100, label=" Start Node")
        nx.draw_networkx_nodes(graph, pos, nodelist=[nearest_end_node], node_color='red', node_size=100, label=" End Node")
        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=[min_distance_parking_node],
            node_color='blue',
            node_size=100,
            label="Parking Node",
        )



        # Draw the legend
        legend_elements = [
            plt.Line2D([0], [0], color='green', marker='o', linestyle='None', markersize=8, label='Start Node'),
            plt.Line2D([0], [0], color='red', marker='o', linestyle='None', markersize=8, label='End Node'),
            plt.Line2D([0], [0], color='blue', marker='o', linestyle='None', markersize=8, label='Parking Node'),
            plt.Line2D([0], [0], color='green', linewidth=2, label=f'Walking Path = {walking_distance/1000:.2f} km'),
            plt.Line2D([0], [0], color='blue', linewidth=2, label=f'Bike Path = {bike_distance/1000:.2f} km'),
            plt.Line2D([0], [0], color='gray', linewidth=1, label='Road Network'),
        ]

        # Add the legend text for total path
        #legend_text_total_path = f'Total Path = {total_distance/1000:.2f} km'
        #legend_elements.append(plt.Line2D([0], [0], color='white', label=legend_text_total_path))

        # Add the legend text
        #legend_text = f'α = {alpha_value:.2f}'
        #egend_elements.append(plt.Line2D([0], [0], color='white', label=legend_text))
        # Convert pos dictionary to a GeoDataFrame
        #gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(*zip(*pos.values())))

        # Set the CRS explicitly
        #gdf.crs = "EPSG:32632"  

        # Add base map using contextily without roads and labels (using CartoDB Positron)
        #ctx.add_basemap(ax=plt.gca(), crs=gdf.crs, source=ctx.providers.CartoDB.Positron, zoom=12)

        plt.legend(handles=legend_elements, loc='upper right')
        
        # Set x and y axis labels in UTM format
        plt.xlabel('X UTM Coordinate')
        plt.ylabel('Y UTM Coordinate')
        # Add legend with text
        plt.axis("equal")
        # Display numeric values of x and y axes on the bottom and left sides
        ax.tick_params(axis='both', which='both', direction='inout', bottom=True, left=True, labelbottom=True, labelleft=True)

        plt.show()

if __name__ == "__main__":
    main()
