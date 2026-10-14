"""
Amah Agent — Verification V0.2

Verification de qualite des resultats, distincte de la simple verification
technique d'execution.

Statuts factuels:
    CONFIRMED     plusieurs sources pertinentes et concordantes
    SUPPORTED     au moins une source pertinente exploitable
    UNCERTAIN     signal faible / sources peu pertinentes
    CONTRADICTED  plusieurs sources pertinentes avec valeurs incompatibles
    MISSING       aucune preuve utile dans les resultats fournis

Cette couche n'affirme jamais qu'une information est vraie uniquement parce
qu'une source la publie. Elle mesure la qualite du soutien fourni par les
resultats collectes.
Compatible Python 3.9.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

PRIMARY_DOMAINS = {
    "apple.com", "support.apple.com"
}
REPUTABLE_DOMAINS = {
    "lesnumeriques.com", "frandroid.com", "theverge.com", "techcrunch.com",
    "gsmarena.com", "arstechnica.com", "cnet.com", "macrumors.com",
    "tomsguide.com", "wired.com", "01net.com", "numerama.com",
}
WEAK_DOMAINS = {
    "facebook.com", "tiktok.com", "youtube.com", "pinterest.com",
}

STOPWORDS = {
    "le","la","les","de","des","du","d","un","une","et","ou","a","au","aux",
    "en","sur","pour","avec","sans","dans","par","est","sont","ce","cette","ces",
    "qui","que","quoi","comment","toutes","tout","les","informations","information",
    "important","importantes","prix","caracteristiques","caracteristique","officiel",
    "guide","2026","2025","resultat","resultats","recherche","cherche","air",
}

@dataclass
class SourceAssessment:
    index: int
    title: str
    url: str
    domain: str
    tier: str
    relevance: float
    useful: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EvidenceAssessment:
    topic: str
    status: str
    detail: str
    source_count: int
    relevant_sources: int
    independent_sources: int
    strong_sources: int
    claims: List[str]
    sources: List[SourceAssessment]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "status": self.status,
            "detail": self.detail,
            "source_count": self.source_count,
            "relevant_sources": self.relevant_sources,
            "independent_sources": self.independent_sources,
            "strong_sources": self.strong_sources,
            "claims": list(self.claims),
            "sources": [s.to_dict() for s in self.sources],
        }


def _norm(text: str) -> str:
    text = str(text or "").lower()
    replacements = {
        "é":"e","è":"e","ê":"e","ë":"e","à":"a","â":"a","ä":"a",
        "î":"i","ï":"i","ô":"o","ö":"o","ù":"u","û":"u","ü":"u","ç":"c",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> List[str]:
    parts = re.findall(r"[a-z0-9][a-z0-9\-]*", _norm(text))
    return [p for p in parts if len(p) >= 3 and p not in STOPWORDS]


def _domain(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _tier(domain: str) -> str:
    if domain in PRIMARY_DOMAINS or any(domain.endswith("." + d) for d in PRIMARY_DOMAINS):
        return "primary"
    if domain in REPUTABLE_DOMAINS or any(domain.endswith("." + d) for d in REPUTABLE_DOMAINS):
        return "reputable"
    if domain in WEAK_DOMAINS or any(domain.endswith("." + d) for d in WEAK_DOMAINS):
        return "weak"
    if domain:
        return "other"
    return "unknown"


def _relevance(query: str, title: str, resume: str) -> float:
    q = set(_tokens(query))
    text = set(_tokens(f"{title} {resume}"))
    if not q:
        return 0.0
    overlap = len(q & text) / max(1, len(q))
    subject_bonus = 0.0
    qn = _norm(query)
    tn = _norm(f"{title} {resume}")
    for phrase in ("iphone 17 air", "iphone air"):
        if phrase in qn and phrase in tn:
            subject_bonus = 0.25
            break
    return min(1.0, overlap + subject_bonus)


def parse_search_results(raw_result: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(str(raw_result or ""))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    items = payload.get("resultats") or payload.get("results") or []
    if not isinstance(items, list):
        return []
    return [x for x in items if isinstance(x, dict)]


def assess_sources(query: str, raw_result: str) -> List[SourceAssessment]:
    items = parse_search_results(raw_result)
    assessments: List[SourceAssessment] = []
    for idx, item in enumerate(items, 1):
        title = str(item.get("titre") or item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        resume = str(item.get("resume") or item.get("snippet") or item.get("description") or "").strip()
        domain = _domain(url)
        tier = _tier(domain)
        relevance = _relevance(query, title, resume)
        useful = relevance >= 0.30
        assessments.append(SourceAssessment(idx, title, url, domain, tier, round(relevance, 3), useful))
    return assessments


def _claim_signals(text: str, topic: str) -> List[str]:
    n = _norm(text)
    claims: List[str] = []
    if any(k in n for k in ("esim only", "esim-only", "sans tiroir sim", "aucun tiroir sim", "sim physique")):
        if "esim" in n:
            claims.append("sim_esim")
    prices = re.findall(r"\b\d[\d\s\.,]{3,}\s*(?:gnf|fg|€|eur|usd|\$)\b", n)
    if prices:
        claims.append("price:" + re.sub(r"\s+", "", prices[0]))
    dims = re.findall(r"\b\d+[\.,]?\d*\s*(?:mm|pouces|\")\b", n)
    if dims:
        claims.append("dimension:" + re.sub(r"\s+", "", dims[0]))
    storage = re.findall(r"\b\d+\s*(?:go|gb|tb)\b", n)
    if storage:
        claims.append("storage:" + re.sub(r"\s+", "", storage[0]))
    if any(k in n for k in ("camera", "appareil photo", "48mp", "48 mpx")):
        claims.append("camera")
    if any(k in n for k in ("autonomie", "batterie", "hours", "heures", "mah")):
        claims.append("battery")
    if any(k in n for k in ("processeur", "chip", "puce", "a19", "a20")):
        claims.append("processor")
    return list(dict.fromkeys(claims))


def _independent_domains(assessments: Iterable[SourceAssessment]) -> int:
    return len({a.domain for a in assessments if a.useful and a.domain})


def verify_web_evidence(query: str, raw_result: str, topic: str = "") -> EvidenceAssessment:
    assessments = assess_sources(query, raw_result)
    useful = [a for a in assessments if a.useful]
    strong = [a for a in useful if a.tier in {"primary", "reputable"}]
    independent = _independent_domains(assessments)

    items = parse_search_results(raw_result)
    all_text = []
    for item in items:
        title = str(item.get("titre") or item.get("title") or "")
        resume = str(item.get("resume") or item.get("snippet") or item.get("description") or "")
        if _relevance(query, title, resume) >= 0.30:
            all_text.append(f"{title} {resume}")

    claims_by_key: Dict[str, List[str]] = {}
    for text in all_text:
        for claim in _claim_signals(text, topic):
            key = claim.split(":", 1)[0]
            claims_by_key.setdefault(key, []).append(claim)

    # Contradiction only when a claim family has multiple distinct concrete values.
    contradicted_families = []
    for key, claims in claims_by_key.items():
        concrete = {c for c in claims if ":" in c}
        if len(concrete) > 1 and key in {"price", "dimension", "storage"}:
            contradicted_families.append(key)

    claim_labels = []
    for key, claims in claims_by_key.items():
        unique = list(dict.fromkeys(claims))
        claim_labels.append(f"{key}={', '.join(unique[:3])}")

    if not assessments or not useful:
        status = "MISSING"
        detail = "Aucune source suffisamment pertinente dans les résultats fournis."
    elif contradicted_families:
        status = "CONTRADICTED"
        detail = "Des sources pertinentes donnent des valeurs différentes pour : " + ", ".join(contradicted_families) + "."
    elif len(useful) >= 2 and independent >= 2:
        status = "CONFIRMED"
        detail = f"{len(useful)} source(s) pertinentes, dont {len(strong)} source(s) fortes, provenant de {independent} domaine(s) indépendant(s)."
    elif strong:
        status = "SUPPORTED"
        detail = f"Au moins une source forte est pertinente ; corroboration indépendante insuffisante ({independent} domaine(s))."
    else:
        status = "UNCERTAIN"
        detail = f"Sources trouvées mais soutien faible ou peu spécialisé ({len(useful)} source(s) pertinentes)."

    return EvidenceAssessment(
        topic=topic or query,
        status=status,
        detail=detail,
        source_count=len(assessments),
        relevant_sources=len(useful),
        independent_sources=independent,
        strong_sources=len(strong),
        claims=claim_labels,
        sources=assessments,
    )


def verify_generic_output(tool_name: str, raw_result: str) -> Dict[str, Any]:
    """Verification générique non-web, volontairement prudente."""
    raw = str(raw_result or "").strip()
    if not raw:
        return {"status": "MISSING", "detail": "Sortie vide.", "checks": {"empty": True}}
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None
    if isinstance(payload, dict) and payload.get("success") is False:
        return {"status": "MISSING", "detail": str(payload.get("error") or "success=false"), "checks": {"success": False}}
    return {"status": "SUPPORTED", "detail": "Sortie présente et exploitable pour une vérification factuelle ultérieure.", "checks": {"present": True}}


__all__ = [
    "SourceAssessment", "EvidenceAssessment", "parse_search_results",
    "assess_sources", "verify_web_evidence", "verify_generic_output",
]
