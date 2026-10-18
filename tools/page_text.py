"""Contenu principal d'une page web (article), sans menu ni bandeaux.

Avant : get_page_text renvoyait inner_text("body") et read_webpage tout le
texte de la page ; sur la plupart des sites, les 2 000 premiers caractères
(ce que voit le modèle) étaient le menu, le bandeau cookies, les liens
"Se connecter"... (test réel du 18/10/2026).

Méthode, sans dépendance (html.parser de la bibliothèque standard) :
1. arbre HTML simplifié ; nav/header/footer/aside/form/script... ignorés, ainsi
   que les blocs dont la classe ou l'id évoque cookies, partage, pub, commentaires ;
2. le bloc retenu est <article>/<main> s'il contient assez de paragraphes,
   sinon le bloc qui contient le plus de texte de paragraphes (méthode
   "Readability" simplifiée) ;
3. texte remis en lignes (un paragraphe, un titre, un élément de liste par ligne).
"""
import re
from html import unescape
from html.parser import HTMLParser

_SKIP = {
    "script", "style", "noscript", "template", "svg", "canvas", "iframe", "object",
    "nav", "header", "footer", "aside", "form", "button", "select", "option",
    "label", "dialog", "menu", "head",
}
_VOID = {"br", "img", "hr", "input", "meta", "link", "area", "base", "col", "embed",
         "source", "track", "wbr", "param"}
_BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "td", "th",
          "dd", "dt", "figcaption", "div", "section", "article", "main", "tr", "ul", "ol",
          "table", "br", "hr"}
_PARAGRAPHS = {"p", "pre", "blockquote"}
# Fermeture implicite : un <p> ou <li> s'arrête au début du suivant
_AUTO_CLOSE = {"p": {"p", "div", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6"},
               "li": {"li"}}
# Toujours écartés, même si le nom évoque aussi du contenu ("related-articles")
_STRONG_NOISE = re.compile(
    r"cookie|consent|gdpr|rgpd|newsletter|subscribe|abonne|share|partag|social|"
    r"related|similaire|comment|promo|advert|\bads?\b|pub-|sponsor|breadcrumb|fil-ariane|"
    r"popup|modal|signup|"
    # Wikipédia : encadré, sommaire, bandeaux, références, liens "modifier"
    r"infobox|navbox|\btoc\b|bandeau|reflist|references|mw-editsection|catlinks|"
    r"coordinates|coordonnees|hatnote|printfooter",
    re.I,
)
# Écartés sauf si le nom évoque aussi du contenu (Wikipédia : la classe du
# <body> contient "…main-menu-pinned…", toute la page partait comme menu)
_WEAK_NOISE = re.compile(r"menu|sidebar|banner|login|connexion|toolbar|skip|metadata", re.I)
_POSITIVE = re.compile(r"article|body|content|contenu|main|post|entry|story|text|texte", re.I)
_NEVER_NOISE = {"html", "body", "main", "article"}


class _Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, attrs or {}, parent, []


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        top = self.stack[-1]
        closes = _AUTO_CLOSE.get(top.tag)
        if closes and tag in closes:
            self.stack.pop()
        node = _Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, dict(attrs), self.stack[-1]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        self.stack[-1].children.append(data)


def _is_noise(node) -> bool:
    if node.tag in _SKIP:
        return True
    if node.attrs.get("aria-hidden") == "true" or "hidden" in node.attrs:
        return True
    if node.attrs.get("role") in ("navigation", "banner", "contentinfo", "complementary", "dialog"):
        return True
    if node.tag in _NEVER_NOISE:
        return False
    marks = f"{node.attrs.get('class') or ''} {node.attrs.get('id') or ''}"
    if _STRONG_NOISE.search(marks):
        return True
    return bool(_WEAK_NOISE.search(marks)) and not _POSITIVE.search(marks)


def _text(node, out, keep_noise=False):
    """Texte du nœud dans out (liste de morceaux, "\n" entre les blocs)."""
    for child in node.children:
        if isinstance(child, str):
            out.append(child)
        elif keep_noise or not _is_noise(child):
            block = child.tag in _BLOCK
            if block:
                out.append("\n")
            _text(child, out)
            if block:
                out.append("\n")


def _clean(chunks) -> str:
    lines, previous = [], None
    for line in "".join(chunks).split("\n"):
        line = re.sub(r"\s+", " ", unescape(line)).replace("¶", "").strip()
        if line and line != previous:
            lines.append(line)
            previous = line
    return "\n".join(lines)


def _paragraph_text(node) -> int:
    """Longueur du texte des paragraphes (hors zones de bruit) sous ce nœud."""
    total = 0
    for child in node.children:
        if isinstance(child, str) or _is_noise(child):
            continue
        if child.tag in _PARAGRAPHS:
            out = []
            _text(child, out)
            size = len(_clean(out))
            total += size if size >= 25 else 0
        else:
            total += _paragraph_text(child)
    return total


def _walk(node):
    for child in node.children:
        if not isinstance(child, str):
            yield child
            if not _is_noise(child):
                yield from _walk(child)


def _best_block(root):
    nodes = list(_walk(root))
    # 1. Balises sémantiques
    semantic = [n for n in nodes if n.tag in ("article", "main") or n.attrs.get("role") == "main"]
    scored = sorted(((_paragraph_text(n), n) for n in semantic), key=lambda x: -x[0])
    if scored and scored[0][0] >= 300:
        return scored[0][1]
    # 2. Bloc qui porte le plus de texte de paragraphes (parent direct + grand-parent / 2)
    scores = {}
    for n in nodes:
        if n.tag in _PARAGRAPHS and n.parent is not None:
            out = []
            _text(n, out)
            size = len(_clean(out))
            if size < 25:
                continue
            scores[id(n.parent)] = (scores.get(id(n.parent), (0, n.parent))[0] + size, n.parent)
            grand = n.parent.parent
            if grand is not None:
                scores[id(grand)] = (scores.get(id(grand), (0, grand))[0] + size / 2, grand)
    if not scores:
        return None
    best = max(scores.values(), key=lambda x: x[0])[1]
    # Remonter tant que le parent n'apporte presque pas d'autre texte (titres, chapeau)
    # (sans aller jusqu'à <body>, qui ramènerait les restes de la page)
    while best.parent is not None and best.parent.tag not in ("root", "html", "body"):
        if _paragraph_text(best.parent) > 1.25 * max(_paragraph_text(best), 1):
            break
        best = best.parent
    return best


def _find_title(root, fallback: str) -> str:
    for n in _walk(root):
        if n.tag == "meta" and n.attrs.get("property") == "og:title" and n.attrs.get("content"):
            return n.attrs["content"].strip()
    for n in _walk(root):
        if n.tag == "h1":
            out = []
            _text(n, out, keep_noise=True)
            title = _clean(out)
            if title:
                return title.replace("¶", "").strip()
    return fallback.replace("¶", "").strip()


def extract_main_text(html: str) -> dict:
    """{"titre", "texte"} : le contenu principal de la page HTML."""
    builder = _TreeBuilder()
    try:
        builder.feed(html or "")
        builder.close()
    except Exception:
        pass
    root = builder.root
    title = _find_title(root, re.sub(r"\s+", " ", builder.title))
    block = _best_block(root)
    out = []
    if block is not None:
        _text(block, out)
    text = _clean(out)
    if len(text) < 200:
        # Page sans vrai article (accueil, liste) : tout le texte hors menus
        body_out = []
        _text(root, body_out)
        body = _clean(body_out)
        if len(body) > len(text):
            text = body
    # Le titre est souvent hors du bloc de l'article : le remettre en tête
    if title and not text.startswith(title):
        text = f"{title}\n{text}" if text else title
    return {"titre": title, "texte": text}
