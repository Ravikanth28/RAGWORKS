from playwright.sync_api import sync_playwright
import time

# Coordinates are centred on open ground / dedicated parking areas so that
# the slot-grid overlay falls on flat, car-friendly terrain rather than
# buildings or road intersections.
LOCATIONS = [
    {
        "name": "Anna Nagar",
        # Anna Nagar Tower Park open ground — large flat circular area
        "url": "https://www.google.com/maps/@13.0906,80.2102,19z/data=!3m1!1e3?entry=ttu",
        "out": "i:/Projects/RAG/frontend/public/anna_nagar_map.png",
    },
    {
        "name": "T Nagar",
        # T Nagar bus terminus open parking ground
        "url": "https://www.google.com/maps/@13.0332,80.2304,19z/data=!3m1!1e3?entry=ttu",
        "out": "i:/Projects/RAG/frontend/public/t_nagar_map.png",
    },
    {
        "name": "Velachery",
        # Velachery MRTS station open ground / bus terminus area
        "url": "https://www.google.com/maps/@12.9789,80.2181,19z/data=!3m1!1e3?entry=ttu",
        "out": "i:/Projects/RAG/frontend/public/velachery_map.png",
    },
    {
        "name": "Mall Parking",
        # Express Avenue Mall — dedicated surface parking lot (south side)
        "url": "https://www.google.com/maps/@13.0583,80.2624,19z/data=!3m1!1e3?entry=ttu",
        "out": "i:/Projects/RAG/frontend/public/mall_parking_map.png",
    },
]

HIDE_UI = [
    "document.querySelectorAll('.app-viewcard-strip').forEach(e => e.remove());",
    "document.querySelectorAll('#omnibox-container').forEach(e => e.remove());",
    "document.querySelectorAll('.scene-footer').forEach(e => e.remove());",
    "document.querySelectorAll('[data-tooltip=\"Show satellite imagery\"]').forEach(e => e.remove());",
]

def take_map_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 800})

        for loc in LOCATIONS:
            print(f"Loading {loc['name']}...")
            page.goto(loc["url"])
            time.sleep(6)  # wait for satellite tiles to fully load
            for js in HIDE_UI:
                page.evaluate(js)
            page.screenshot(path=loc["out"])
            print(f"Captured {loc['name']} → {loc['out']}")

        browser.close()
        print("Done.")

if __name__ == "__main__":
    take_map_screenshots()
