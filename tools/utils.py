import ast
import operator
import secrets
import string
from datetime import datetime, timedelta


# ── Calculatrice ─────────────────────────────────────────────────────────────

_OPS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.Mod:  operator.mod,
    ast.USub: operator.neg,
}

def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError(f"Operation non autorisee : {node}")

def calculate(expression: str) -> dict:
    """
    Calcule une expression mathématique.
    Exemples : '15% de 250', '(120 + 80) * 1.2', '2 ** 10'
    """
    try:
        # Remplacement % de X par /100*X
        expr = expression.lower()
        if "% de" in expr or "% of" in expr:
            parts = expr.replace("% de", "% *").replace("% of", "% *").split("%")
            pct   = float(parts[0].strip())
            val   = float(parts[1].replace("*", "").strip())
            result = pct / 100 * val
            return {"success": True, "expression": expression, "resultat": round(result, 4)}

        tree   = ast.parse(expr, mode='eval')
        result = _eval(tree.body)
        return {"success": True, "expression": expression, "resultat": round(result, 6)}
    except Exception as e:
        return {"error": f"Expression invalide : {e}"}


# ── Date et heure ────────────────────────────────────────────────────────────

def get_datetime() -> dict:
    """Retourne la date, l'heure et le jour de la semaine actuels."""
    now    = datetime.now()
    jours  = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois   = ["janvier", "février", "mars", "avril", "mai", "juin",
               "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return {
        "success":       True,
        "date":          now.strftime("%d/%m/%Y"),
        "heure":         now.strftime("%H:%M:%S"),
        "jour":          jours[now.weekday()],
        "mois":          mois[now.month - 1],
        "annee":         now.year,
        "timestamp":     now.isoformat(),
    }


def add_days(days: int) -> dict:
    """Calcule la date dans X jours (ou il y a X jours si négatif)."""
    target = datetime.now() + timedelta(days=days)
    jours  = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return {
        "success": True,
        "dans":    f"{days} jours",
        "date":    target.strftime("%d/%m/%Y"),
        "jour":    jours[target.weekday()],
    }


# ── Générateur de mot de passe ───────────────────────────────────────────────

def generate_password(length: int = 16, include_symbols: bool = True) -> dict:
    """Génère un mot de passe sécurisé."""
    try:
        chars = string.ascii_letters + string.digits
        if include_symbols:
            chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        pwd = ''.join(secrets.choice(chars) for _ in range(length))
        return {"success": True, "mot_de_passe": pwd, "longueur": length}
    except Exception as e:
        return {"error": str(e)}


# ── Convertisseur d'unités ───────────────────────────────────────────────────

_CONVERSIONS = {
    # Distance
    ("km", "miles"):   0.621371,
    ("miles", "km"):   1.60934,
    ("m", "ft"):       3.28084,
    ("ft", "m"):       0.3048,
    ("cm", "in"):      0.393701,
    ("in", "cm"):      2.54,
    # Poids
    ("kg", "lbs"):     2.20462,
    ("lbs", "kg"):     0.453592,
    ("g", "oz"):       0.035274,
    ("oz", "g"):       28.3495,
    # Température (gérée à part)
    # Surface
    ("m2", "ft2"):     10.7639,
    ("ft2", "m2"):     0.092903,
    # Volume
    ("l", "gal"):      0.264172,
    ("gal", "l"):      3.78541,
    ("ml", "fl oz"):   0.033814,
    ("fl oz", "ml"):   29.5735,
}

def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convertit une valeur d'une unité à une autre."""
    try:
        fu, tu = from_unit.lower().strip(), to_unit.lower().strip()

        # Température
        if fu == "celsius" and tu in ("fahrenheit", "f"):
            result = value * 9/5 + 32
        elif fu in ("fahrenheit", "f") and tu in ("celsius", "c"):
            result = (value - 32) * 5/9
        elif fu in ("celsius", "c") and tu in ("kelvin", "k"):
            result = value + 273.15
        elif fu in ("kelvin", "k") and tu in ("celsius", "c"):
            result = value - 273.15
        elif (fu, tu) in _CONVERSIONS:
            result = value * _CONVERSIONS[(fu, tu)]
        else:
            return {"error": f"Conversion '{from_unit}' → '{to_unit}' non supportée"}

        return {
            "success":    True,
            "valeur":     value,
            "de":         from_unit,
            "vers":       to_unit,
            "resultat":   round(result, 4),
            "formatte":   f"{value} {from_unit} = {round(result, 4)} {to_unit}",
        }
    except Exception as e:
        return {"error": str(e)}
