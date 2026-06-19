from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect

# -----------------------------------------------------------------------------
# STUDENT TODO FILE
# Advanced inference hooks called by the framework-owned backtracking engine.
# If these are not implemented, the engine can still run for partial credit.
# -----------------------------------------------------------------------------


def forward_check(problem: CSPProblem, variable: str, value: Rect, assignment: Assignment, domains: dict[str, list[Rect]]) -> dict[str, list[Rect]] | None:
    """
    Return a pruned copy of domains after assigning variable=value.
    Return None if any unassigned variable gets an empty domain.
    """
    raise NotImplementedError('TODO: implement forward_check() in student/inference.py')


def ac3(problem: CSPProblem, domains: dict[str, list[Rect]]) -> dict[str, list[Rect]] | None:
    """
    Optional AC-3 preprocessing. Return reduced domains, or None if
    inconsistency is detected.
    """
    raise NotImplementedError('TODO: implement ac3() in student/inference.py')
