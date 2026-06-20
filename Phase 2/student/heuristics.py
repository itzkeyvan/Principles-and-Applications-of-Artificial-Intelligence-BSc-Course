from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect
from .consistency import is_consistent

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
    best_var = None
    best_count = float('inf')
    best_degree = -1

    for var in problem.variables:
        if var in assignment:
            continue

        # Count the number of compatible values
        count = 0
        for val in domains[var]:
            if is_consistent(problem, assignment, var, val):
                count += 1

        # Degree (number of adverbs in which this variable participates)
        degree = sum(1 for c in problem.constraints if var in c.variables)

        # MRV first priority, degree to break the equation
        if count < best_count or (count == best_count and degree > best_degree):
            best_count = count
            best_degree = degree
            best_var = var

    return best_var


def order_domain_values(problem: CSPProblem, variable: str, assignment: Assignment, domains: dict[str, list[Rect]]) -> list[Rect]:
    """
    Return the candidate values for `variable` in the order the framework engine
    should try them.

    Required: implement LCV (least constraining value). Values that remove
    fewer options from the remaining variables should be tried earlier.
    """
    raise NotImplementedError('TODO: implement order_domain_values() in student/heuristics.py')
