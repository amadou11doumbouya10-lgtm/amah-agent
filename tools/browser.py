from playwright.sync_api import sync_playwright, Browser, Page
import atexit
import logging

log = logging.getLogger("amah.browser")

_playwright = None
_browser: Browser = None
_page: Page = None


def _close_browser():
    global _browser, _playwright
    try:
        if _browser and _browser.is_connected():
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception as e:
        log.debug(f"Fermeture du navigateur ignoree : {e}")


atexit.register(_close_browser)


def _ensure_browser():
    global _playwright, _browser, _page
    if _browser is None or not _browser.is_connected():
        try:
            _playwright = sync_playwright().start()
            _browser    = _playwright.chromium.launch(headless=False)
            _page       = _browser.new_page()
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e).lower():
                raise RuntimeError(
                    "Le navigateur Chrome n'est pas installé.\n"
                    "Lance le fichier 'installer_navigateur.bat' une seule fois,\n"
                    "puis relance Amah."
                )
            raise
    return _page


def open_browser(url: str) -> dict:
    try:
        page = _ensure_browser()
        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        return {"success": True, "url": page.url, "titre": page.title()}
    except Exception as e:
        return {"error": str(e)}


def click_element(selector: str) -> dict:
    try:
        page = _ensure_browser()
        page.click(selector, timeout=8000)
        page.wait_for_load_state("domcontentloaded")
        return {"success": True, "clique": selector, "url": page.url}
    except Exception as e:
        return {"error": str(e)}


def fill_form(selector: str, value: str) -> dict:
    try:
        page = _ensure_browser()
        page.fill(selector, value, timeout=8000)
        return {"success": True, "champ": selector, "valeur": value}
    except Exception as e:
        return {"error": str(e)}


def take_screenshot(path: str = None) -> dict:
    try:
        from pathlib import Path
        page = _ensure_browser()
        if not path:
            from datetime import datetime
            import sys
            base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
            path = str(base / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        page.screenshot(path=path, full_page=False)
        return {"success": True, "fichier": path}
    except Exception as e:
        return {"error": str(e)}


def get_page_text() -> dict:
    try:
        page = _ensure_browser()
        text = page.inner_text("body")
        if len(text) > 5000:
            text = text[:5000] + "\n\n[... tronqué ...]"
        return {"success": True, "url": page.url, "titre": page.title(), "texte": text}
    except Exception as e:
        return {"error": str(e)}
