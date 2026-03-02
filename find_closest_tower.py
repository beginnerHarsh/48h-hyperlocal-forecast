import requests
import config
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees).
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers.
    return c * r

url = config.IMD_API
res = requests.get(url).json()

print(f"Loaded {len(res)} stations. Scanning for closest physical tower...")

# Calculate math distance for all 3000 towers
valid_stations = []
for station in res:
    try:
        lat_str = station.get('Latitude')
        lon_str = station.get('Longitude')
        
        if lat_str is not None and lon_str is not None:
            if str(lat_str).strip() and str(lon_str).strip():
                s_lat = float(lat_str)
                s_lon = float(lon_str)
                
                if s_lat == 0.0 or s_lon == 0.0:
                    continue
                    
                distance_km = haversine(config.LOCAL_LON, config.LOCAL_LAT, s_lon, s_lat)
                station['distance_km'] = distance_km
                valid_stations.append(station)
    except Exception as e:
        pass

valid_stations.sort(key=lambda x: x['distance_km'])

print("\n--- TOP CLOSEST IMD STATIONS ---")
for i in range(min(5, len(valid_stations))):
    s = valid_stations[i]
    print(f"{i+1}. {s['STATION']} ({s['ID']})")
    print(f"   Distance: {s['distance_km']:.2f} km")
    print(f"   Current Temp: {s.get('CURR_TEMP')}°C")
    print(f"   Coordinates: {s['Latitude']}, {s['Longitude']}")
    print("-" * 30)
