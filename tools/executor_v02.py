"""Amah Agent — Executor V0.2 + Verification V0.2."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, Optional

from tools.verification_v02 import verify_generic_output, verify_web_evidence


@dataclass
class VerificationResult:
    status: str
    detail: str
    checks: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "detail": self.detail, "checks": dict(self.checks)}


@dataclass
class ExecutionRecord:
    tool_name: str
    step_id: str
    action: str
    purpose: str
    args: Dict[str, Any]
    raw_result: str
    elapsed_ms: float
    verification: VerificationResult


def _parse_json(raw_result: str) -> Optional[Any]:
    try:
        return json.loads(str(raw_result or ""))
    except Exception:
        return None


def verify_result(tool_name: str, args: Dict[str, Any], raw_result: str, purpose: str = "") -> VerificationResult:
    raw = str(raw_result or "")
    payload = _parse_json(raw)
    if isinstance(payload, dict):
        if payload.get("success") is False:
            return VerificationResult("MISSING", str(payload.get("error") or "success=false"), {"success": False})
        if payload.get("error"):
            return VerificationResult("MISSING", str(payload.get("error")), {"error": True})

    if tool_name == "web_search":
        query = str(args.get("query") or "").strip()
        evidence = verify_web_evidence(query, raw, topic=query)
        return VerificationResult(evidence.status, evidence.detail, evidence.to_dict())

    if tool_name in {"screenshot_full", "take_screenshot"}:
        path_value = args.get("path")
        if path_value:
            path = Path(str(path_value))
            if path.exists() and path.is_file() and path.stat().st_size > 0:
                return VerificationResult("CONFIRMED", "fichier de capture présent et non vide", {"file_exists": True})
            return VerificationResult("MISSING", "le fichier de capture attendu est absent ou vide", {"file_exists": False})

    if tool_name == "open_browser":
        if isinstance(payload, dict) and payload.get("success") is True and payload.get("url"):
            return VerificationResult("CONFIRMED", "navigation confirmée par l'outil", {"url_present": True})

    if tool_name == "get_weather":
        if isinstance(payload, dict) and payload.get("success") is True and payload.get("ville"):
            return VerificationResult("SUPPORTED", "données météo structurées reçues", {"city_present": True})

    if tool_name == "calculate":
        if isinstance(payload, dict):
            for key in ("value", "resultat", "result", "answer", "calculation"):
                if key in payload:
                    return VerificationResult("CONFIRMED", "résultat de calcul présent", {"value_present": True})
        elif raw.strip():
            return VerificationResult("CONFIRMED", "résultat de calcul texte présent", {"value_present": True})

    generic = verify_generic_output(tool_name, raw)
    return VerificationResult(generic["status"], generic["detail"], generic["checks"])


def execute_verified_step(step: Any, runner: Callable[[str, Optional[dict]], str]) -> ExecutionRecord:
    tool_name = str(getattr(step, "tool_name", "") or "")
    step_id = str(getattr(step, "step_id", "") or "")
    action = str(getattr(step, "action", "") or "")
    purpose = str(getattr(step, "purpose", "") or "")
    args = dict(getattr(step, "args", {}) or {})

    started = perf_counter()
    raw_result = runner(tool_name, args)
    elapsed_ms = (perf_counter() - started) * 1000
    verification = verify_result(tool_name, args, raw_result, purpose=purpose)

    return ExecutionRecord(tool_name, step_id, action, purpose, args, raw_result, elapsed_ms, verification)


def format_verification_line(record: ExecutionRecord) -> str:
    return (
        f"[EXECUTOR V0.2] {record.step_id} terminé "
        f"| {record.elapsed_ms:.1f} ms "
        f"| vérification={record.verification.status} "
        f"| {record.verification.detail}"
    )


__all__ = ["VerificationResult", "ExecutionRecord", "verify_result", "execute_verified_step", "format_verification_line"]
