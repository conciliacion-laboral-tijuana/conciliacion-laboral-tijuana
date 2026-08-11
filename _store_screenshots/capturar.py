"""Captura las 3 vistas del listing para la Chrome Web Store a 1280x800."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent

VISTAS = [
    ("vista1_popup.html", "captura_1_popup.png"),
    ("vista2_llenado.html", "captura_2_llenado.png"),
    ("vista3_exito.html", "captura_3_exito.png"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
    for html, out in VISTAS:
        url = (BASE / html).as_uri()
        page.goto(url)
        page.wait_for_timeout(400)
        page.screenshot(path=str(BASE / out), full_page=False)
        print("OK", out)
    browser.close()
print("DONE")
