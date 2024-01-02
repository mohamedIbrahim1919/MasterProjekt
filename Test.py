import networkx as nx
import matplotlib.pyplot as plt
import geopandas as gpd

# Function to calculate shortest biking paths
def shortest_bike_paths(graph, start_node):
    return nx.single_source_dijkstra_path_length(graph.reverse(), start_node, weight='length_biking')

# Function to calculate shortest walking paths
def shortest_walking_paths(graph, target_node):
    return nx.single_source_dijkstra_path_length(graph, target_node, weight='length_walking')

# Function to visualize shortest paths
def visualize_shortest_paths(graph, start_node, target_node, shortest_bike_path, shortest_walking_path):
    pos = nx.spring_layout(graph)  # You can choose another layout if needed
    labels = nx.get_node_attributes(graph, "label")
    
    nx.draw(graph, pos, with_labels=True, labels=labels, font_weight='bold', node_size=1000, node_color='lightblue')
    
    # Draw the shortest biking path in red
    nx.draw_networkx_edges(graph, pos, edgelist=shortest_bike_path, edge_color='red', width=2.0, label='Shortest Biking Path')
    
    # Draw the shortest walking path in blue
    nx.draw_networkx_edges(graph, pos, edgelist=shortest_walking_path, edge_color='blue', width=2.0, label='Shortest Walking Path')
    
    plt.legend()
    plt.show()

# Load GeoJSON file into GeoDataFrame
gdf = gpd.read_file('C:/Contents/MileStone_14.12.23/MileStone_14.12.23/Bonn Cycle Network.geojson')

# Create a graph from the GeoDataFrame
G = nx.DiGraph()
for index, row in gdf.iterrows():
    G.add_edge(row['source'], row['target'], length_walking=row['length_walking'], length_biking=row['length_biking'])

# Prompt the user to enter start and target nodes
start_node = input("Enter the start node: ")
target_node = input("Enter the target node: ")

# Calculate shortest paths
shortest_bike_paths_result = shortest_bike_paths(G, start_node)
shortest_walking_paths_result = shortest_walking_paths(G, target_node)

# Print results (modify as needed)
print("Shortest Bike Paths:", shortest_bike_paths_result)
print("Shortest Walking Paths:", shortest_walking_paths_result)

# Visualize the graph and the shortest paths
shortest_bike_path_nodes = nx.shortest_path(G.reverse(), source=start_node, weight='length_biking')
shortest_walking_path_nodes = nx.shortest_path(G, source=target_node, weight='length_walking')

visualize_shortest_paths(G, start_node, target_node, shortest_bike_path_nodes, shortest_walking_path_nodes)
