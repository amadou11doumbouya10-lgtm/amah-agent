# Playwright (~0,3 s) est chargé à la première action du navigateur
# (_ensure_browser), plus au démarrage d'Amah
import atexit
import functools
import logging
import queue
import sys
import threading
from concurrent.futures import Future
from pathlib import Path

log = logging.getLogger("amah.browser")

_playwright = None
_context = None   # playwright BrowserContext
_page = None      # playwright Page

_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent
_PROFILE_DIR = str(_BASE / "browser_profile")

# Flag Chromium standard qui retire le marqueur d'automatisation
# (navigator.webdriver=true + bandeau "controle par un logiciel de test").
# Sans lui, Google affiche systematiquement une page "trafic exceptionnel"
# (CAPTCHA) sur toute recherche faite via Playwright.
_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]

# Playwright (API synchrone) refuse qu'un autre fil utilise le navigateur qu'il
# a ouvert : gui.py traite chaque message dans un nouveau fil, donc "ouvre X"
# marchait puis "lis la page" échouait au message suivant ("cannot switch to
# a different thread"). Toutes les actions passent par ce fil unique.
_jobs: "queue.Queue" = queue.Queue()
_worker = None
_worker_lock = threading.Lock()


def _browser_worker():
    while True:
        fn, args, kwargs, future = _jobs.get()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:
            future.set_exception(exc)


def _on_browser_thread(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        global _worker
        if threading.current_thread() is _worker:
            return fn(*args, **kwargs)
        with _worker_lock:
            if _worker is None or not _worker.is_alive():
                _worker = threading.Thread(target=_browser_worker, name="amah-browser", daemon=True)
                _worker.start()
        future = Future()
        _jobs.put((fn, args, kwargs, future))
        return future.result(timeout=180)
    return wrapper


def _close_browser():
    if _worker is None or not _worker.is_alive():
        return
    try:
        _on_browser_thread(_close_browser_now)()
    except Exception as e:
        log.debug(f"Fermeture du navigateur ignoree : {e}")


def _close_browser_now():
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
                from playwright.sync_api import sync_playwright
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


@_on_browser_thread
def open_browser(url: str) -> dict:
    try:
        page = _ensure_browser()
    except Exception as e:
        return {"error": str(e)}
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        return {"success": True, "url": page.url, "titre": page.title()}
    except Exception as first_error:
        # Adresse dictée mal transcrite ("site.nu.vercel.app" pour "site-nu") :
        # on essaie les variantes probables avant d'abandonner
        # (nouvel onglet : la page d'erreur du navigateur interromprait sinon
        # la navigation suivante)
        global _page
        from tools.search import url_variants
        for variant in url_variants(url):
            tab = None
            try:
                tab = page.context.new_page()
                tab.goto(variant, timeout=15000)
                tab.wait_for_load_state("domcontentloaded")
                try:
                    page.close()
                except Exception:
                    pass
                _page = tab
                return {"success": True, "url": tab.url, "titre": tab.title(),
                        "note": f"L'adresse {url} ne répondait pas ; {variant} a marché "
                                "(erreur de dictée probable)."}
            except Exception:
                if tab is not None:
                    try:
                        tab.close()
                    except Exception:
                        pass
        return {"error": str(first_error)}


@_on_browser_thread
def click_element(selector: str) -> dict:
    try:
        page = _ensure_browser()
        page.click(selector, timeout=8000)
        page.wait_for_load_state("domcontentloaded")
        return {"success": True, "clique": selector, "url": page.url}
    except Exception as e:
        return {"error": str(e)}


@_on_browser_thread
def fill_form(selector: str, value: str) -> dict:
    try:
        page = _ensure_browser()
        page.fill(selector, value, timeout=8000)
        return {"success": True, "champ": selector, "valeur": value}
    except Exception as e:
        return {"error": str(e)}


@_on_browser_thread
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


@_on_browser_thread
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


# Champs de formulaire tels que l'utilisateur les voit : libellé (label for=,
# label parent, aria-label, placeholder, nom). Le modèle ne voyait que le texte
# de la page : il essayait "Email" là où le champ s'appelle "E-mail" (18 s
# perdues par essai) et ne savait pas quels champs remplir (test du 19/10/2026).
_FIELD_HELPERS = r"""
const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
const labelEl = el => (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]')) || el.closest('label');
const labelOf = el => {
  const l = labelEl(el);
  return ((l && l.innerText) || el.getAttribute('aria-label') || el.placeholder || el.title
          || el.name || el.id || '').replace(/\s+/g, ' ').trim();
};
const norm = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
const fields = () => [...document.querySelectorAll('input, textarea, select')]
  .map((el, i) => ({el, i}))
  .filter(({el}) => !['hidden', 'submit', 'button', 'image', 'reset', 'file'].includes(el.type)
    && (visible(el) || ((el.type === 'checkbox' || el.type === 'radio') && labelEl(el) && visible(labelEl(el)))));
"""

_LIST_FIELDS_JS = "() => {" + _FIELD_HELPERS + r"""
  const champs = fields().slice(0, 40).map(({el}) => {
    const f = {champ: labelOf(el).slice(0, 80),
               type: el.tagName === 'SELECT' ? 'liste' : el.tagName === 'TEXTAREA' ? 'texte long' : (el.type || 'text')};
    if (el.tagName === 'SELECT') f.choix = [...el.options].map(o => o.text.trim()).filter(Boolean).slice(0, 25);
    if (el.type === 'checkbox' || el.type === 'radio') f.coche = el.checked;
    else if (el.value) f.rempli = true;
    if (el.required) f.obligatoire = true;
    return f;
  });
  const boutons = [...document.querySelectorAll('button, input[type=submit], input[type=button]')]
    .filter(visible).map(b => (b.innerText || b.value || b.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean).slice(0, 20);
  return {champs, boutons};
}"""

# Meilleur champ pour un libellé donné, sans tenir compte des accents, tirets
# et majuscules ("Email" -> "E-mail", "téléphone" -> "Numéro de téléphone")
_FIND_FIELD_JS = "({q, bool}) => {" + _FIELD_HELPERS + r"""
  const want = norm(q);
  let best = null, bestScore = 0;
  for (const {el, i} of fields()) {
    // Une case à cocher ne reçoit que oui/non : "contact" + un numéro ne doit
    // pas tomber sur la case id="contact_consent"
    if (!bool && (el.type === 'checkbox' || el.type === 'radio')) continue;
    const names = [labelOf(el), el.getAttribute('aria-label'), el.placeholder, el.name, el.id, el.title]
      .map(norm).filter(n => n.length >= 3);
    for (const n of names) {
      // Mot contenu dans le libellé : seulement un libellé court ("contact"
      // ne doit pas trouver la case "… ils vous contactent : cet accord …")
      const partial = want.length >= 3 && (n.startsWith(want)
        || (n.length <= Math.max(30, want.length * 4) && (n.includes(want) || want.includes(n))));
      const s = n === want ? 3 : partial ? 2 : 0;
      if (s > bestScore) { best = [i, labelOf(el), el.tagName === 'SELECT' ? 'select' : (el.type || 'text')]; bestScore = s; }
    }
  }
  return best;
}"""

_PICK_OPTION_JS = r"""(el, q) => {
  const norm = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const w = norm(q);
  const o = [...el.options].find(o => norm(o.text) === w)
         || [...el.options].find(o => norm(o.text).length >= 2 && (norm(o.text).includes(w) || w.includes(norm(o.text))));
  return o ? o.value : null;
}"""

_TRUE_WORDS = {"", "oui", "yes", "true", "1", "coche", "coché", "cocher", "vrai", "on"}
_FALSE_WORDS = {"non", "no", "false", "0", "decoche", "décoché", "décocher", "faux", "off"}


def _form_summary(page):
    """{"champs": [...], "boutons": [...]} de la page, ou None sans formulaire."""
    try:
        data = page.evaluate(_LIST_FIELDS_JS)
        return data if data.get("champs") else None
    except Exception:
        return None


def _fill_found_field(page, index: int, kind: str, text: str):
    locator = page.locator("input, textarea, select").nth(index)
    if kind == "select":
        value = locator.evaluate(_PICK_OPTION_JS, text)
        if value is None:
            choices = locator.evaluate("el => [...el.options].map(o => o.text.trim()).filter(Boolean)")
            raise ValueError(f"Choix introuvable : '{text}'. Choix possibles : {', '.join(choices[:25])}")
        locator.select_option(value=value, timeout=3000)
    elif kind in ("checkbox", "radio"):
        if str(text).strip().lower() in _TRUE_WORDS or kind == "radio":
            locator.check(force=True, timeout=3000)
        else:
            locator.uncheck(force=True, timeout=3000)
    else:
        locator.fill(text, timeout=5000)


@_on_browser_thread
def type_in_field(label: str, text: str) -> dict:
    """Ecrit du texte dans un champ identifie par son label/placeholder/nom -- pas besoin de selecteur CSS."""
    try:
        page = _ensure_browser()
        try:
            is_bool = str(text).strip().lower() in _TRUE_WORDS | _FALSE_WORDS
            found = page.evaluate(_FIND_FIELD_JS, {"q": label, "bool": is_bool})
        except Exception:
            found = None
        if found:
            index, field_label, kind = found
            try:
                _fill_found_field(page, index, kind, text)
                shown = "(masqué)" if kind == "password" else text
                return {"success": True, "champ": field_label, "valeur": shown}
            except ValueError as e:
                return {"error": str(e)}
            except Exception:
                pass                    # repli : localisateurs Playwright ci-dessous
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
                locator.wait_for(state="visible", timeout=1000)
                locator.fill(text, timeout=3000)
                return {"success": True, "champ": label, "valeur": text}
            except Exception:
                continue
        form = _form_summary(page)
        error = {"error": f"Aucun champ trouve pour : '{label}'"}
        if form:
            error["champs_disponibles"] = [f["champ"] for f in form["champs"]]
        return error
    except Exception as e:
        return {"error": str(e)}


def _main_text(page) -> dict:
    """Contenu principal de la page (article), sans menus ni bandeaux."""
    from tools.page_text import extract_main_text
    result = extract_main_text(page.content())
    if len(result["texte"]) < 200:
        body = page.inner_text("body")
        if len(body) > len(result["texte"]):
            result["texte"] = body
    return {"url": page.url, "titre": result["titre"] or page.title(), "texte": result["texte"]}


@_on_browser_thread
def get_page_text() -> dict:
    try:
        page = _ensure_browser()
        data = _main_text(page)
        text, total = data["texte"], len(data["texte"])
        if total > 8000:
            text = text[:8000] + "\n\n[... tronqué ...]"
        result = {"success": True, "url": data["url"], "titre": data["titre"]}
        form = _form_summary(page)
        if form:
            # Avant le texte : le résultat est tronqué à 4 000 caractères
            result["formulaire"] = form
        result.update(texte=text, longueur_totale=total)
        return result
    except Exception as e:
        return {"error": str(e)}


@_on_browser_thread
def current_page_main_text():
    """Texte complet de la page déjà ouverte, ou None si aucune page n'est
    ouverte (n'ouvre pas de navigateur). Utilisé par read_aloud."""
    if _page is None:
        return None
    try:
        if _page.is_closed() or _page.url in ("", "about:blank"):
            return None
        return _main_text(_page)
    except Exception:
        return None


@_on_browser_thread
def open_and_read(url: str) -> dict:
    """Ouvre l'URL dans le navigateur et renvoie son texte complet : pour les
    sites qui refusent les requêtes simples (403) ou se construisent en JavaScript."""
    page = _ensure_browser()
    page.goto(url, timeout=20000)
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    return _main_text(page)
