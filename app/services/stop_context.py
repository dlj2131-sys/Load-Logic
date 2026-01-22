import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from rapidfuzz import fuzz  # type: ignore
except Exception:  # pragma: no cover
    fuzz = None  # fallback below

import difflib

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "stop_context.json"


def load_context_db() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _token_set_ratio_fallback(a: str, b: str) -> int:
    # Simple fallback: normalize tokens, compare as strings
    ta = " ".join(sorted(a.replace(",", " ").lower().split()))
    tb = " ".join(sorted(b.replace(",", " ").lower().split()))
    return int(difflib.SequenceMatcher(None, ta, tb).ratio() * 100)


def best_match(address: str, entries: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], int]:
    if not entries:
        return None, 0
    best: Optional[Dict[str, Any]] = None
    best_score = 0
    for e in entries:
        m = e.get("match", "")
        if not m:
            continue
        if fuzz is not None:
            score = int(fuzz.token_set_ratio(address, m))  # forgiving with order/commas
        else:
            score = _token_set_ratio_fallback(address, m)
        if score > best_score:
            best_score = score
            best = e

    if best and best_score >= 90:
        return best, best_score
    return None, best_score


def get_stop_context(address: str, default_service_minutes: int) -> Dict[str, Any]:
    """Lightweight local lookup: fuzzy match an address to local context notes."""
    entries = load_context_db()
    hit, score = best_match(address, entries)

    if not hit:
        return {"service_minutes": default_service_minutes, "notes": [], "time_window": None, "match_score": score}

    return {
        "service_minutes": int(hit.get("service_minutes", default_service_minutes)),
        "notes": list(hit.get("notes", [])),
        "time_window": hit.get("time_window"),
        "match_score": score,
    }
