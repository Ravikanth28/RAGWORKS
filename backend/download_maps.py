from playwright.sync_api import sync_playwright
import time

def take_map_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 800})
        
        # Anna Nagar
        page.goto("https://www.google.com/maps/@13.0846,80.2179,18z/data=!3m1!1e3?entry=ttu")
        time.sleep(5) # wait for map to load
        # hide UI elements
        page.evaluate("document.querySelectorAll('.app-viewcard-strip').forEach(e => e.remove());")
        page.evaluate("document.querySelectorAll('#omnibox-container').forEach(e => e.remove());")
        page.screenshot(path="i:/Projects/RAG/frontend/public/anna_nagar_map.png")
        print("Captured Anna Nagar")
        
        # T Nagar
        page.goto("https://www.google.com/maps/@13.0405,80.2337,18z/data=!3m1!1e3?entry=ttu")
        time.sleep(5)
        page.evaluate("document.querySelectorAll('.app-viewcard-strip').forEach(e => e.remove());")
        page.evaluate("document.querySelectorAll('#omnibox-container').forEach(e => e.remove());")
        page.screenshot(path="i:/Projects/RAG/frontend/public/t_nagar_map.png")
        print("Captured T Nagar")

        browser.close()

if __name__ == "__main__":
    take_map_screenshots()
