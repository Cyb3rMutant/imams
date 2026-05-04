from geopy.distance import geodesic
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="khateeb_app")

loc1 = geolocator.geocode("BS34 7LF, UK")
loc2 = geolocator.geocode("BS16 1FP, UK")

coords_1 = (loc1.latitude, loc1.longitude)
coords_2 = (loc2.latitude, loc2.longitude)

distance_km = geodesic(coords_1, coords_2).km
print(distance_km)
