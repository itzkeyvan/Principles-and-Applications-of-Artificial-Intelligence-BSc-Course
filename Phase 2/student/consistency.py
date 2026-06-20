from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect
from planforge.core.geometry import inside_boundary, overlaps
from planforge.core.constraints import constraint_is_satisfied
# -----------------------------------------------------------------------------
# STUDENT TODO FILE
# Required function:
#   - is_consistent
# -----------------------------------------------------------------------------


def is_consistent(problem: CSPProblem, assignment: Assignment, variable: str, value: Rect) -> bool:
    """
    Return True iff assigning `value` to `variable` does not violate any hard
    constraint with the current partial assignment.

    You should check at least:
      - the rectangle is inside the apartment boundary
      - the room area is inside its allowed range
      - it does not overlap already assigned rooms
      - all relevant unary/binary constraints that are currently checkable

    Useful helpers are available in:
      - planforge.core.geometry
      - planforge.core.constraints
    """
    # 1) inside_boundary
    if not inside_boundary(value, problem.width, problem.height):
        return False

    # 2) Allowed area
    spec = problem.room_specs[variable]
    if not (spec.min_area <= value.area <= spec.max_area):
        return False

    # 3) No overlap
    for assigned_var, assigned_rect in assignment.items():
        if overlaps(value, assigned_rect):
            return False
        
    # 4) Explicit constraints
    temp_assignment = dict(assignment)
    temp_assignment[variable] = value
    for constraint in problem.constraints:
        if not constraint_is_satisfied(problem, constraint, temp_assignment):
            return False

    return True
