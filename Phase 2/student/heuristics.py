from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect

# -----------------------------------------------------------------------------
# STUDENT TODO FILE
# Required: select_unassigned_variable with MRV
# Required: order_domain_values with LCV
# -----------------------------------------------------------------------------


def select_unassigned_variable(problem: CSPProblem, assignment: Assignment, domains: dict[str, list[Rect]]) -> str:
    """
    Choose the next unassigned variable for the framework backtracking engine.

    Required: implement MRV (minimum remaining values). A degree heuristic
    tie-breaker is recommended.
    """
    raise NotImplementedError('TODO: implement select_unassigned_variable() in student/heuristics.py')


def order_domain_values(problem: CSPProblem, variable: str, assignment: Assignment, domains: dict[str, list[Rect]]) -> list[Rect]:
    """
    Return the candidate values for `variable` in the order the framework engine
    should try them.

    Required: implement LCV (least constraining value). Values that remove
    fewer options from the remaining variables should be tried earlier.
    """
    raise NotImplementedError('TODO: implement order_domain_values() in student/heuristics.py')
