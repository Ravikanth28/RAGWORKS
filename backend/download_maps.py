"""
Download satellite-style map screenshots for each parking location.

Uses Leaflet.js served from a local HTML page so we get clean satellite
imagery (Esri World Imagery) with NO UI chrome.

Each location is centred on an open ground / surface-parking area so
that the slot grid overlay sits on flat, buildingless terrain.
"""
from playwright.sync_api import sync_playwright
import time

# lat, lon centred on real open/surface parking areas
LOCATIONS = [
    {
        "name": "Anna Nagar",
        # Anna Nagar Tower Park — centered on the big open sandy brown ground
        "lat": 13.0892, "lon": 80.2093, "zoom": 18,
        "out": "i:/Projects/RAG/frontend/public/anna_nagar_map.png",
    },
    {
        "name": "T Nagar",
        # Valluvar Kottam heritage park open ground
        "lat": 13.0442, "lon": 80.2399, "zoom": 18,
        "out": "i:/Projects/RAG/frontend/public/t_nagar_map.png",
    },
    {
        "name": "Velachery",
        # Velachery MRTS / Taramani open grounds — flat tarmac
        "lat": 12.9812, "lon": 80.2317, "zoom": 18,
        "out": "i:/Projects/RAG/frontend/public/velachery_map.png",
    },
    {
        "name": "Mall Parking",
        # Express Avenue Mall outer surface parking area
        "lat": 13.0604, "lon": 80.2602, "zoom": 18,
        "out": "i:/Projects/RAG/frontend/public/mall_parking_map.png",
    },
]

# Leaflet page that shows ONLY the Esri satellite layer — no markers, no UI
def make_html(lat, lon, zoom=18):
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ margin:0; padding:0; }}
  #map {{ width:1000px; height:800px; }}
</style>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head>
<body>
<div id="map"></div>
<script>
  var map = L.map('map', {{
    center: [{lat}, {lon}],
    zoom: {zoom},
    zoomControl: false,
    attributionControl: false
  }});
  L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
    {{ maxZoom: 20 }}
  ).addTo(map);
</script>
</body>
</html>"""


def take_map_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 800})

        for loc in LOCATIONS:
            print(f"Loading {loc['name']}...")
            html = make_html(loc["lat"], loc["lon"], loc.get("zoom", 18))
            page.set_content(html)
            # wait for all satellite tiles to finish loading
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            page.screenshot(path=loc["out"])
            print(f"Captured {loc['name']} → {loc['out']}")

        browser.close()
        print("Done.")


if __name__ == "__main__":
    take_map_screenshots()

