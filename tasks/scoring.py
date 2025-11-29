from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict


# Strategy weights
STRATEGY_WEIGHTS: Dict[str, Dict[str, float]] = {
    # Focus: small, quick tasks first
    "fastest_wins": {
        "urgency": 0.20,
        "importance": 0.20,
        "effort": 0.50,
        "deps": 0.10,
    },
    # Focus: high impact / importance
    "high_impact": {
        "urgency": 0.20,
        "importance": 0.60,
        "effort": 0.10,
        "deps": 0.10,
    },
    # Focus: strict on deadlines
    "deadline_driven": {
        "urgency": 0.60,
        "importance": 0.20,
        "effort": 0.10,
        "deps": 0.10,
    },
    # Balanced default strategy
    "smart_balance": {
        "urgency": 0.35,
        "importance": 0.35,
        "effort": 0.15,
        "deps": 0.15,
    },
}


# Helpers

def _parse_due_date(value: Any) -> Optional[date]:
    
    if value is None or value == "":
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        try:
            # Expecting ISO 8601 format from JSON / DRF: "YYYY-MM-DD"
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            # Fallback: unparsable string -> treat as no due date
            return None

    # Unknown type
    return None


def compute_urgency_score(due_date: Any) -> float:
    
    d = _parse_due_date(due_date)
    if d is None:
        return 0.3  # neutral if no date

    today = date.today()
    delta_days = (d - today).days

    if delta_days < 0:
        return 1.0   # overdue
    elif delta_days == 0:
        return 0.9   # due today
    elif delta_days <= 3:
        return 0.8
    elif delta_days <= 7:
        return 0.6
    elif delta_days <= 14:
        return 0.4
    else:
        return 0.2   # far in future


def compute_effort_score(estimated_hours: Any) -> float:
    
    try:
        h = float(estimated_hours)
    except (TypeError, ValueError):
        return 0.5  # neutral if unknown

    if h <= 0:
        return 0.5
    if h <= 1:
        return 1.0
    if h <= 3:
        return 0.7
    if h <= 6:
        return 0.4
    return 0.2  # big task


def normalize_importance(importance: Any) -> float:
    """
    Normalize importance from 1–10 to 0–1.

    """
    try:
        imp = int(importance)
    except (TypeError, ValueError):
        imp = 5  # default mid-importance

    if imp < 1:
        imp = 1
    if imp > 10:
        imp = 10

    return imp / 10.0


def detect_cycles(tasks_by_id: Dict[Any, Dict[str, Any]]) -> Set[Any]:
    
    graph: Dict[Any, List[Any]] = {
        tid: t.get("dependencies", []) or []
        for tid, t in tasks_by_id.items()
    }

    visited: Dict[Any, str] = {}  # "white" (absent), "gray", "black"
    in_cycle: Set[Any] = set()

    def dfs(node: Any, stack: List[Any]) -> None:
        visited[node] = "gray"
        stack.append(node)

        for dep in graph.get(node, []):
            if dep not in visited:
                dfs(dep, stack)
            elif visited[dep] == "gray":
                # Found a cycle: mark all nodes from first occurrence of dep
                idx = stack.index(dep)
                in_cycle.update(stack[idx:])

        visited[node] = "black"
        stack.pop()

    for node in graph.keys():
        if node not in visited:
            dfs(node, [])

    return in_cycle


def compute_dependency_bonus(tasks: List[Dict[str, Any]]) -> Dict[Any, float]:
    
    dependents_count = defaultdict(int)
    
    # Count how many tasks list each ID as a dependency
    for t in tasks:
        deps = t.get("dependencies") or []
        for dep in deps:
            dependents_count[dep] += 1

    bonus: Dict[Any, float] = {}
    for t in tasks:
        tid = t.get("id")
        n = dependents_count.get(tid, 0)

        if n == 0:
            bonus[tid] = 0.0
        elif n == 1:
            bonus[tid] = 0.3
        elif n <= 3:
            bonus[tid] = 0.6
        else:
            bonus[tid] = 1.0

    return bonus


# Main scoring entry point
def score_tasks(
    tasks: List[Dict[str, Any]],
    strategy: str = "smart_balance",
) -> List[Dict[str, Any]]:
    weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS["smart_balance"])

    # Build lookup for cycle detection
    tasks_by_id: Dict[Any, Dict[str, Any]] = {
        t["id"]: t for t in tasks if "id" in t
    }

    cycles = detect_cycles(tasks_by_id)
    dep_bonus = compute_dependency_bonus(tasks)

    # First: compute scores and explanations for all tasks
    scored: List[Dict[str, Any]] = []

    for t in tasks:
        tid = t.get("id")

        urgency = compute_urgency_score(t.get("due_date"))
        importance = normalize_importance(t.get("importance"))
        effort = compute_effort_score(t.get("estimated_hours"))
        deps = dep_bonus.get(tid, 0.0)

        base_score = (
            urgency   * weights["urgency"]
            + importance * weights["importance"]
            + effort   * weights["effort"]
            + deps     * weights["deps"]
        )

        # Penalty for being in a circular dependency
        if tid in cycles:
            base_score -= 0.2

        explanation_parts: List[str] = []

        if urgency >= 0.8:
            explanation_parts.append("Due very soon")
        elif urgency >= 0.6:
            explanation_parts.append("Upcoming deadline")

        if importance >= 0.8:
            explanation_parts.append("Very important")
        elif importance >= 0.6:
            explanation_parts.append("Important")

        if effort >= 0.7:
            explanation_parts.append("Quick win")
        elif effort <= 0.3:
            explanation_parts.append("Large effort task")

        if deps > 0:
            explanation_parts.append("Unblocks other tasks")

        if tid in cycles:
            explanation_parts.append("Part of circular dependency (penalized)")

        if not explanation_parts:
            explanation = (
                "Balanced priority based on urgency, importance, "
                "effort, and dependencies."
            )
        else:
            explanation = "; ".join(explanation_parts)

        scored.append({
            **t,
            "score": round(float(base_score), 3),
            "explanation": explanation,
        })

    scored_by_id: Dict[Any, Dict[str, Any]] = {
        t["id"]: t for t in scored if "id" in t
    }

    non_cycle_ids = [tid for tid in scored_by_id.keys() if tid not in cycles]
    cycle_ids = [tid for tid in scored_by_id.keys() if tid in cycles]

    # Build graph for non-circular tasks: edges dep -> task
    indegree: Dict[Any, int] = {tid: 0 for tid in non_cycle_ids}
    adj: Dict[Any, List[Any]] = {tid: [] for tid in non_cycle_ids}

    for tid in non_cycle_ids:
        t = tasks_by_id.get(tid, {})
        deps = t.get("dependencies") or []
        for dep in deps:
            if dep in indegree:  # only count dependencies that are also in this set
                indegree[tid] += 1
                adj.setdefault(dep, []).append(tid)

    # Kahn's algorithm variant:
    # always pick the available node with the highest score
    ordered_ids: List[Any] = []
    available: List[Any] = [
        tid for tid in non_cycle_ids if indegree.get(tid, 0) == 0
    ]

    while available:
        # pick the highest-score task among available
        best_id = max(
            available,
            key=lambda _tid: scored_by_id[_tid].get("score", 0.0)
        )
        available.remove(best_id)
        ordered_ids.append(best_id)

        for nxt in adj.get(best_id, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                available.append(nxt)

    # Any remaining non-circular tasks (e.g., due to missing IDs) – just sort by score
    remaining_non_cycle = [
        tid for tid in non_cycle_ids if tid not in ordered_ids
    ]
    remaining_non_cycle.sort(
        key=lambda _tid: scored_by_id[_tid].get("score", 0.0),
        reverse=True,
    )

    # Circular tasks: already penalized; place them at the end, highest score first
    cycle_ids.sort(
        key=lambda _tid: scored_by_id[_tid].get("score", 0.0),
        reverse=True,
    )

    final_order_ids = ordered_ids + remaining_non_cycle + cycle_ids
    final_tasks = [scored_by_id[tid] for tid in final_order_ids]

    return final_tasks


__all__ = [
    "score_tasks",
    "compute_urgency_score",
    "compute_effort_score",
    "normalize_importance",
    "detect_cycles",
    "compute_dependency_bonus",
    "STRATEGY_WEIGHTS",
]
