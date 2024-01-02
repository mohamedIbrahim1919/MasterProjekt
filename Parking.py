import json
import os

# Parse the GeoJSON data for parking nodes
def parse_parking_geojson():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    #print("Script Directory:", script_directory)
    parking_files = ['BikeParking_City_Admin.geojson', 'Nextbike_bike_sharing_bonn.geojson', 'OSM_bike_parking_bonn.geojson']
    parking_nodes = []

    for file in parking_files:
        file_path = os.path.join(script_directory, file)
        if os.path.isfile(file_path):
            with open(file_path, encoding='utf-8') as f:
                parking_data = json.load(f)

            for feature in parking_data['features']:
                try:
                    if feature['geometry']['type'] == 'Point':
                        coordinates = tuple(feature['geometry']['coordinates'])
                        parking_nodes.append(coordinates)
                except Exception as e:
                    print(f"Error processing feature in file '{file}': {e}")
                    print("Problematic feature:", feature)
                    continue
    return parking_nodes

if __name__ == '__main__':
    parking_nodes = parse_parking_geojson()
    print("Number of Parking Nodes:", len(parking_nodes))
