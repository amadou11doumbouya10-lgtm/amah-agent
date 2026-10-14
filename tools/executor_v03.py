"""Amah Agent — Executor V0.3 + Verification V0.3.

Adds one controlled auto-recovery attempt when a web-search step returns
MISSING or CONTRADICTED evidence. The recovery is deliberately bounded to
one extra search per step and never loops recursively.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Dict, Optional

from tools.executor_v02 import ExecutionRecord, VerificationResult, verify_result


RECOVERABLE_STATUSES = {"MISSING", "CONTRADICTED", "UNCERTAIN"}


def _clean_topic(topic: str) -> str:
    return " ".join(str(topic or "").strip().split())


def build_recovery_query(step: Any, topic: str) -> Optional[str]:
    tool_name = str(getattr(step, "tool_name", "") or "")
    if tool_name != "web_search":
        return None
    step_id = str(getattr(step, "step_id", "") or "")
    purpose = str(getattr(step, "purpose", "") or "")
    args = dict(getattr(step, "args", {}) or {})
    base = _clean_topic(topic) or _clean_topic(args.get("query"))
    if not base:
        return None

    low = f"{step_id} {purpose}".lower()
    if "sim" in low or "esim" in low:
        return f"{base} SIM physique eSIM plateau nano-SIM variantes pays Apple Support"
    if "price" in low or "prix" in low or "dispon" in low:
        return f"{base} prix Guinée Conakry GNF 2026 disponibilité revendeur"
    if "camera" in low or "battery" in low or "autonomie" in low or "performance" in low:
        return f"{base} caméra batterie autonomie performances test GSMArena Frandroid Les Numériques"
    if "spec" in low or "caracter" in low or "design" in low:
        return f"{base} caractéristiques officielles Apple Support dimensions écran puce stockage"
    return f"{base} information vérifiée source officielle détails"


def execute_verified_step_with_recovery(
    step: Any,
    runner: Callable[[str, Optional[dict]], str],
    topic: str = "",
    perf_log: bool = True,
) -> Dict[str, Any]:
    """Execute une étape puis, si nécessaire, effectue une seule recherche corrective."""
    from tools.executor_v02 import execute_verified_step

    primary = execute_verified_step(step=step, runner=runner)
    bundle: Dict[str, Any] = {"record": primary, "recovery": None}

    if primary.tool_name != "web_search" or primary.verification.status not in RECOVERABLE_STATUSES:
        return bundle

    recovery_query = build_recovery_query(step, topic)
    if not recovery_query:
        return bundle

    recovery_step_id = f"{primary.step_id}_recovery"
    recovery_args = {"query": recovery_query, "num_results": 5}

    recovery_step = type("RecoveryStep", (), {
        "step_id": recovery_step_id,
        "tool_name": "web_search",
        "action": "search",
        "purpose": f"Recherche corrective après {primary.verification.status.lower()}",
        "args": recovery_args,
    })()

    started = perf_counter()
    raw_result = runner("web_search", recovery_args)
    elapsed_ms = (perf_counter() - started) * 1000
    verification = verify_result("web_search", recovery_args, raw_result, purpose=recovery_step.purpose)
    recovery_record = ExecutionRecord(
        tool_name="web_search",
        step_id=recovery_step_id,
        action="search",
        purpose=recovery_step.purpose,
        args=recovery_args,
        raw_result=raw_result,
        elapsed_ms=elapsed_ms,
        verification=verification,
    )

    bundle["recovery"] = {"for_step": primary.step_id, "record": recovery_record}
    return bundle


def format_verification_line(record: ExecutionRecord, prefix: str = "[EXECUTOR V0.3] ") -> str:
    return (
        f"{prefix}{record.step_id} terminé "
        f"| {record.elapsed_ms:.1f} ms "
        f"| vérification={record.verification.status} "
        f"| {record.verification.detail}"
    )


__all__ = [
    "ExecutionRecord", "VerificationResult", "execute_verified_step_with_recovery",
    "build_recovery_query", "format_verification_line",
]
