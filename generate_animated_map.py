import os
import glob
import json
import math
import random
import folium
from folium.plugins import TimestampedGeoJson
from datetime import datetime, timedelta

# Optional: geometry simplification (speeds up large polygons)
try:
    from shapely.geometry import shape, mapping
    _HAS_SHAPELY = True
except Exception:
    _HAS_SHAPELY = False

# Tunable performance knobs
POINT_CAP_PER_FILE = 200  # Max point features per file (downsample if exceeded)
SIMPLIFY_TOLERANCE_DEGREES = 0.005  # ~100m at equator; adjust as needed

# Create a map centered on a specific location (canvas improves rendering performance)
m = folium.Map(
    location=[48.3794, 31.1656],
    zoom_start=5,
    tiles="CartoDB positron",
    width="70%",
    height="70%",
    prefer_canvas=True,
)

# Get all points and polygons GeoJSON files from the data folder
files = sorted(glob.glob('data/*_points.geojson') + glob.glob('data/*_polygons.geojson'))

# Prepare data for TimestampedGeoJson
all_features = []
for file in files:
    date_str = os.path.basename(file).split('_')[2]
    current_date = datetime.strptime(date_str, '%Y%m%d')

    with open(file, 'r') as f:
        data = json.load(f)

    # Split by geometry type to optionally thin/simplify
    point_features = []
    polygon_features = []

    for feature in data.get('features', []):
        geom = feature.get('geometry')
        if not geom:
            continue
        geom_type = geom.get('type')
        if geom_type == 'Point':
            point_features.append(feature)
        elif geom_type in ['Polygon', 'MultiPolygon']:
            polygon_features.append(feature)
        else:
            # Keep other geometry types as-is
            polygon_features.append(feature)

    # Downsample dense point sets to reduce render load
    if POINT_CAP_PER_FILE and len(point_features) > POINT_CAP_PER_FILE:
        step = math.ceil(len(point_features) / POINT_CAP_PER_FILE)
        point_features = point_features[::step]

    # Simplify polygons to reduce vertex count
    if _HAS_SHAPELY and SIMPLIFY_TOLERANCE_DEGREES and SIMPLIFY_TOLERANCE_DEGREES > 0:
        simplified = []
        for feat in polygon_features:
            try:
                shp = shape(feat['geometry'])
                shp_simplified = shp.simplify(SIMPLIFY_TOLERANCE_DEGREES, preserve_topology=True)
                feat['geometry'] = mapping(shp_simplified)
            except Exception:
                # If any feature fails to simplify, keep original geometry
                pass
            simplified.append(feat)
        polygon_features = simplified

    # Re-style and timestamp features
    for feature in polygon_features + point_features:
        feature.setdefault('properties', {})
        feature['properties']['time'] = current_date.isoformat()
        geom_type = feature['geometry']['type']

        if geom_type in ['Polygon', 'MultiPolygon']:
            feature['properties']['style'] = {
                'fillColor': '#8B0000',
                'color': '#8B0000',
                'weight': 0.5,
                'opacity': 0.7,
                'fillOpacity': 0.55,
            }
        elif geom_type == 'Point':
            feature['properties']['icon'] = 'circle'
            feature['properties']['iconstyle'] = {
                'fillColor': '#8B0000',
                'color': '#8B0000',
                'radius': 2,
                'weight': 0,
                'opacity': 0.9,
                'fillOpacity': 0.8,
            }
        all_features.append(feature)

# Create the TimestampedGeoJson layer
TimestampedGeoJson(
    {'type': 'FeatureCollection', 'features': all_features},
    period='P1D',
    add_last_point=False,
    duration='P1D',  # show only the current day's features
    auto_play=False,
    loop=False,
    max_speed=20,
    loop_button=True,
    date_options='YYYY-MM-DD',
    time_slider_drag_update=False
).add_to(m)

# Display the map
m.save('animated_map.html')