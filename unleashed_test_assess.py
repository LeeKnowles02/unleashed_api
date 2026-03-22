from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple


def _as_key_set(keys: Sequence[Tuple[str, str]]) -> Set[str]:
    return {f"{k1}|{k2}" for k1, k2 in keys}


def _completeness_pct(rows: int, required_fields_ok: int) -> float:
    if rows == 0:
        return 0.0
    return round((required_fields_ok / rows) * 100.0, 2)


def assess_incremental_validation(
    *,
    control_keys: Sequence[Tuple[str, str]],
    batch1_keys: Sequence[Tuple[str, str]],
    batch2_keys: Sequence[Tuple[str, str]],
    control_rows: int,
    incremental_rows: int,
    required_fields_ok: int,
    checkpoint_progressed: bool,
) -> Dict[str, Any]:
    control_set = _as_key_set(control_keys)
    batch1_set = _as_key_set(batch1_keys)
    batch2_set = _as_key_set(batch2_keys)
    inc_set = batch1_set.union(batch2_set)

    overlap_count = len(batch1_set.intersection(batch2_set))
    missing_count = len(control_set.difference(inc_set))
    extra_count = len(inc_set.difference(control_set))
    complete_pct = _completeness_pct(incremental_rows, required_fields_ok)

    row_count_assessment = "PASS" if control_rows == incremental_rows else "FAIL"
    key_match_assessment = "PASS" if missing_count == 0 and extra_count == 0 else "FAIL"
    checkpoint_assessment = "PASS" if checkpoint_progressed else "FAIL"

    fail_reasons = []
    warn_reasons = []

    if overlap_count > 0:
        fail_reasons.append("overlap")
    if row_count_assessment == "FAIL":
        fail_reasons.append("row_count_mismatch")
    if key_match_assessment == "FAIL":
        fail_reasons.append("key_mismatch")
    if checkpoint_assessment == "FAIL":
        fail_reasons.append("checkpoint")

    if complete_pct < 95.0:
        fail_reasons.append("critical_fields_below_threshold")
    elif complete_pct < 100.0:
        warn_reasons.append("critical_fields_not_100pct")

    if fail_reasons:
        overall = "FAIL"
        sign_off = "NOT_READY"
    elif warn_reasons:
        overall = "PASS_WITH_WARNINGS"
        sign_off = "NOT_READY"
    else:
        overall = "PASS"
        sign_off = "READY_FOR_PRODUCTION"

    return {
        "OverallAssessment": overall,
        "SignOffStatus": sign_off,
        "ControlRowCount": control_rows,
        "IncrementalRowCount": incremental_rows,
        "OverlapCount": overlap_count,
        "MissingCount": missing_count,
        "ExtraCount": extra_count,
        "CriticalFieldCompletenessPct": complete_pct,
        "CheckpointAssessment": checkpoint_assessment,
        "RowCountAssessment": row_count_assessment,
        "KeyMatchAssessment": key_match_assessment,
        "Notes": ";".join(fail_reasons + warn_reasons) if (fail_reasons or warn_reasons) else "All checks passed.",
    }
