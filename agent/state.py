"""AgentState TypedDict and custom reducers."""

import operator
from typing import Annotated, Any, TypedDict


def merge_evidence(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge new evidence into existing, accumulating lists and preserving latest scalars."""
    merged = dict(existing)
    for key, value in new.items():
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            seen = {str(item) for item in merged[key]}
            for item in value:
                if str(item) not in seen:
                    merged[key].append(item)
                    seen.add(str(item))
        elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_evidence(merged[key], value)
        else:
            merged[key] = value
    return merged


class AgentState(TypedDict):
    procedure: dict  # objective, assertion, control_id, account, period
    plan: str
    tool_calls: Annotated[list[dict], operator.add]
    evidence: Annotated[dict, merge_evidence]
    reasoning_trace: Annotated[list[str], operator.add]
    workpaper: dict
    act_count: int
