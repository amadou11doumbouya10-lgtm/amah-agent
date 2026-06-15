from playwright.sync_api import sync_playwright, BrowserContext, Page
import atexit
import logging
import sys
from pathlib import Path

log = logging.getLogger("amah.browser")

_playwright = None
_context: BrowserContext = None
_page: Page = None

_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent
_PROFILE_DIR = str(_BASE / "browser_profile")

# Flag Chromium standard qui retire le marqueur d'automatisation
# (navigator.webdriver=true + bandeau "controle par un logiciel de test").
# Sans lui, Google affiche systematiquement une page "trafic exceptionnel"
# (CAPTCHA) sur toute recherche faite via Playwright.
_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]


def _close_browser():
    global _context, _playwright
    try:
        if _context:
            _context.close()
        if _playwright:
            _playwright.stop()
    except Exception as e:
        log.debug(f"Fermeture du navigateur ignoree : {e}")


atexit.register(_close_browser)


def _launch_context(p):
    """Lance le vrai Edge (profil persistant Amah, garde cookies/connexions
    entre les sessions) -- repli sur Chromium embarque si Edge n'est pas
    installe (rare sur Windows 11)."""
    try:
        return p.chromium.launch_persistent_context(
            _PROFILE_DIR, channel="msedge", headless=False, args=_LAUNCH_ARGS,
        )
    except Exception as e:
        if "msedge" in str(e).lower() or "channel" in str(e).lower():
            return p.chromium.launch_persistent_context(
                _PROFILE_DIR, headless=False, args=_LAUNCH_ARGS,
            )
        raise


def _ensure_browser():
    global _playwright, _context, _page
    page_ok = _page is not None
    if page_ok:
        try:
            page_ok = not _page.is_closed()
        except Exception:
            page_ok = False
    if not page_ok:
        if _context is not None:
            try:
                _page = _context.new_page()
                return _page
            except Exception:
                _context = None
        try:
            if _playwright is None:
                _playwright = sync_playwright().start()
            _context = _launch_context(_playwright)
            _page    = _context.pages[0] if _context.pages else _context.new_page()
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e).lower():
                raise RuntimeError(
                    "Le navigateur n'est pas installé.\n"
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


def click_text(text: str) -> dict:
    """Clique sur l'element (bouton, lien, texte) correspondant au texte visible donne -- pas besoin de selecteur CSS."""
    try:
        page = _ensure_browser()
        strategies = [
            lambda: page.get_by_role("button", name=text, exact=False),
            lambda: page.get_by_role("link", name=text, exact=False),
            lambda: page.get_by_text(text, exact=False),
            lambda: page.get_by_label(text, exact=False),
        ]
        for strat in strategies:
            try:
                locator = strat().first
                locator.wait_for(state="visible", timeout=3000)
                locator.click(timeout=5000)
                page.wait_for_load_state("domcontentloaded")
                return {"success": True, "clique": text, "url": page.url}
            except Exception:
                continue
        return {"error": f"Aucun element cliquable trouve pour : '{text}'"}
    except Exception as e:
        return {"error": str(e)}


def type_in_field(label: str, text: str) -> dict:
    """Ecrit du texte dans un champ identifie par son label/placeholder/nom -- pas besoin de selecteur CSS."""
    try:
        page = _ensure_browser()
        strategies = [
            lambda: page.get_by_label(label, exact=False),
            lambda: page.get_by_placeholder(label, exact=False),
            lambda: page.get_by_role("textbox", name=label, exact=False),
            # Barres de recherche (Google, Bing...) : souvent role=combobox/
            # searchbox avec un aria-label abrege ("Rech.") mais un attribut
            # title complet ("Rechercher") -- aucune des strategies ci-dessus
            # ne les detecte.
            lambda: page.get_by_role("combobox", name=label, exact=False),
            lambda: page.get_by_role("searchbox", name=label, exact=False),
            lambda: page.get_by_title(label, exact=False),
        ]
        for strat in strategies:
            try:
                locator = strat().first
                locator.wait_for(state="visible", timeout=3000)
                locator.fill(text, timeout=5000)
                return {"success": True, "champ": label, "valeur": text}
            except Exception:
                continue
        return {"error": f"Aucun champ trouve pour : '{label}'"}
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
