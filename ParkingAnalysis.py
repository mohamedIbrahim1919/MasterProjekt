import json
import os
import sys
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
from Network import calculate_shortest_safest_path, find_nearest_node, read_graph
from Parking import parse_parking_geojson, haversine_distance
from utils import get_category_color, parse_geojson, distance
import utm
import networkx as nx

from typing import List, Tuple, Union, Dict


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


def parking_analysis(start_node: Tuple, end_node: Tuple, alphaa: float):
    # Parse parking information from geojson
    parking_nodes = parse_parking_geojson()
    # print(parking_nodes)
    graph = read_graph(alphaa)  # Initialize graph with a default value
    add_parking_to_graph(graph, parking_nodes)  # Add parking nodes to the graph

    try:
        # Check if the end node is a parking node
        if end_node in parking_nodes:
            # Calculate the normal shortest path
            shortest_path, total_length, graph = calculate_shortest_safest_path(graph, start_node, end_node)
            print("Walking Distance: 0 km")
            print("Shortest Distance from Source to Parking Node:", total_length, "km")
            print("Total Distance:", total_length, "km")
            return shortest_path, total_length, graph, None, parking_nodes

        # If the end node is not a parking node, find the nearest parking node
        nearest_parking_node = find_nearest_node(parking_nodes, end_node)

        # Calculate the shortest path from start node to the nearest parking node
        shortest_path_to_parking, total_length_to_parking, graph = calculate_shortest_safest_path(
            graph, start_node, nearest_parking_node
        )

        # Check if the calculation was successful
        if shortest_path_to_parking is not None:
            # Calculate walking distance from parking node to end node
            walking_distance = haversine_distance(
                nearest_parking_node[1], nearest_parking_node[0], end_node[1], end_node[0]
            )

            # Calculate the total length as the sum of the two segments
            total_length = total_length_to_parking + walking_distance

            print("Walking Distance:", walking_distance, "km")
            print("Shortest Distance from Source to Parking Node:", total_length_to_parking, "km")
            print("Total Distance:", total_length, "km")

            # Calculate walking time, bike time, and total time
            average_walking_speed = 4  # km/h
            average_bike_speed = 15  # km/h
            walking_time = (walking_distance / average_walking_speed) * 60
            bike_time = (total_length_to_parking / average_bike_speed) * 60
            total_time = walking_time + bike_time

            print("Walking Time: {:.2f} minutes".format(walking_time))
            print("Bike Time: {:.2f} minutes".format(bike_time))
            print("Total Time: {:.2f} minutes".format(total_time))

            return shortest_path_to_parking, total_length, graph, nearest_parking_node, parking_nodes
        else:
            print("Error: No path found from source to the nearest parking node.")
            return None, 0, graph, None, parking_nodes

    except Exception as e:
        # Handle encoding issues when printing the error message
        encoded_error = str(e).encode(sys.stdout.encoding, errors="replace")
        print("Error:", encoded_error.decode(sys.stdout.encoding))
        return None, 0, graph, None, parking_nodes  # Return default values in case of an error


if __name__ == "__main__":
    # Set the working directory to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    start_x, start_y = 7.096886, 50.740125
    end_x, end_y = 7.1148233, 50.7381129
    alphaa = 1

    # Get user input for start node, end node, and alphaa
    # start_x, start_y = map(float, input("Enter the start node coordinates (x y): ").split())
    # end_x, end_y = map(float, input("Enter the end node coordinates (x y): ").split())
    # alphaa = float(input("Enter the value of alphaa:"))

    # Create start and end node coordinates
    start_node = (start_x, start_y)
    end_node = (end_x, end_y)

    nearest_parking_node = None  # Initialize nearest_parking_node before the try block
    walking_distance = 0  # Initialize walking_distance before the try block
    total_length_to_parking = 0  # Initialize total_length_to_parking before the try block
    parking_nodes = None  # Initialize parking_nodes before the try block

    try:
        # Perform parking analysis
        shortest_path, total_length, graph, nearest_parking_node, parking_nodes = parking_analysis(
            start_node, end_node, alphaa
        )

        if shortest_path:
            # print("Shortest path:", shortest_path)

            # Extract x and y coordinates from the shortest path
            x_coords = [coord[1] for coord in shortest_path]
            y_coords = [coord[0] for coord in shortest_path]

            # Prepare colors for different categories
            category_colors = {
                "designated paths": "green",
                "shared with pedestrian": "blue",
                "shared with cars": "orange",
                "No Infrastructure": "red",
            }

            # Create a colormap from the category colors
            colormap = ListedColormap(category_colors.values())

            # Load GeoJSON data
            geojson_data = parse_geojson()

            # Plot the graph with original colors
            plt.figure(figsize=(8, 8))

            # Set the bounding box to include the start and end nodes
            plt.xlim(min(start_x, end_x) - 0.005, max(start_x, end_x) + 0.005)
            plt.ylim(min(start_y, end_y) - 0.005, max(start_y, end_y) + 0.005)

            for feature in geojson_data["features"]:
                if feature["geometry"]["type"] == "LineString":
                    coordinates = np.array(feature["geometry"]["coordinates"])
                    properties = feature["properties"]
                    category = get_category_color(properties, category_colors)  # Get the category color
                    plt.plot(coordinates[:, 0], coordinates[:, 1], color=category, alpha=0.5)

            # Plot the shortest path with original colors but bolder
            for i in range(len(y_coords) - 1):
                current_coord = tuple(shortest_path[i])
                next_coord = tuple(shortest_path[i + 1])
                edge_data = graph.get_edge_data(current_coord, next_coord)
                category = edge_data["category"]
                plt.plot([y_coords[i], y_coords[i + 1]], [x_coords[i], x_coords[i + 1]], color=category, linewidth=6)

            # ...

            # ...

            if nearest_parking_node is not None:
                # Print the corrected coordinates before plotting
                print("Corrected Nearest Parking Node Coordinates:", nearest_parking_node)

                # If the end node is not a parking node or walking distance is greater than zero, update walking_distance
                if end_node not in parking_nodes or walking_distance > 0:
                    walking_distance = haversine_distance(
                        nearest_parking_node[1], nearest_parking_node[0], end_node[1], end_node[0]
                    )

                    # Plot the start and end nodes with different colors
                    start_node_color = "black"
                    end_node_color = "orange"
                    nearest_parking_color = "blue"

                    plt.scatter(y_coords[0], x_coords[0], color=start_node_color, s=100, label="Start Node", zorder=10)
                    plt.scatter(y_coords[-1], x_coords[-1], color=end_node_color, s=100, label="End Node", zorder=10)

                    # Plot the nearest parking node with a blue marker
                    plt.scatter(
                        nearest_parking_node[0],
                        nearest_parking_node[1],
                        color="blue",
                        s=200,
                        label="Nearest Parking Node",
                        zorder=10,
                    )

                    # Plot a line from the end node to the nearest parking node
                    plt.plot(
                        [y_coords[-1], nearest_parking_node[0]],
                        [x_coords[-1], nearest_parking_node[1]],
                        color="black",
                        linestyle="-",
                        linewidth=2,
                        label=f"Path to Nearest Parking (Walking Distance: {walking_distance:.2f} km)",
                    )

                    # Add a legend for start and end nodes, category colors, nearest parking node, nearest road node, and total length
                    legend_handles = [
                        plt.Line2D(
                            [0],
                            [0],
                            marker="o",
                            color="w",
                            markerfacecolor=start_node_color,
                            markersize=10,
                            label="Start Node",
                        ),
                        plt.Line2D(
                            [0],
                            [0],
                            marker="o",
                            color="w",
                            markerfacecolor=end_node_color,
                            markersize=10,
                            label="End Node",
                        ),
                        plt.Line2D(
                            [0],
                            [0],
                            marker="o",
                            color="w",
                            markerfacecolor=nearest_parking_color,
                            markersize=8,
                            label=f"Nearest Parking Node (Walking Distance: {walking_distance:.2f} km)",
                        ),
                        plt.Line2D(
                            [0],
                            [0],
                            linestyle="None",
                            marker="None",
                            label=f"Total Shortest Path Distance: {total_length:.2f} km",
                        ),
                        *[
                            plt.Line2D(
                                [0],
                                [0],
                                linestyle="None",
                                marker="o",
                                color="w",
                                markerfacecolor=color,
                                markersize=8,
                                label=f"{category}",
                            )
                            for category, color in category_colors.items()
                        ],
                    ]

                    # Place the legend in the top right corner
                    plt.legend(handles=legend_handles, loc="upper right")

                    plt.xlabel("Latitude")
                    plt.ylabel("Longitude")
                    plt.title("Shortest Path Visualization")

                    # Save the figure before showing it
                    plt.savefig("path_visualization.png", dpi=1080)
                    plt.show()

                else:
                    # Plot the start and end nodes with different colors
                    start_node_color = "black"
                    end_node_color = "orange"

                    plt.scatter(y_coords[0], x_coords[0], color=start_node_color, s=100, label="Start Node", zorder=10)
                    plt.scatter(y_coords[-1], x_coords[-1], color=end_node_color, s=100, label="End Node", zorder=10)

                    # Add a legend for start and end nodes, category colors, nearest road node, and total length
                    legend_handles = [
                        plt.Line2D(
                            [0],
                            [0],
                            marker="o",
                            color="w",
                            markerfacecolor=start_node_color,
                            markersize=10,
                            label="Start Node",
                        ),
                        plt.Line2D(
                            [0],
                            [0],
                            marker="o",
                            color="w",
                            markerfacecolor=end_node_color,
                            markersize=10,
                            label="End Node",
                        ),
                        plt.Line2D(
                            [0],
                            [0],
                            linestyle="None",
                            marker="None",
                            label=f"Total Shortest Path Distance: {total_length:.2f} km",
                        ),
                        *[
                            plt.Line2D(
                                [0],
                                [0],
                                linestyle="None",
                                marker="o",
                                color="w",
                                markerfacecolor=color,
                                markersize=8,
                                label=f"{category}",
                            )
                            for category, color in category_colors.items()
                        ],
                    ]

                    # Place the legend in the top right corner
                    plt.legend(handles=legend_handles, loc="upper right")

                    plt.xlabel("Latitude")
                    plt.ylabel("Longitude")
                    plt.title("Shortest Path Visualization")

                    # Save the figure before showing it
                    plt.savefig("path_visualization.png", dpi=1080)
                    plt.show()

            else:
                print("No path found between the start and end nodes.")

    except Exception as e:
        print("Error:", str(e))
