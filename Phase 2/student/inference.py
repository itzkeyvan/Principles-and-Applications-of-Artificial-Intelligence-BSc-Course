from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect
from planforge.core.constraints import constraint_is_satisfied
from .consistency import is_consistent
from collections import deque

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
    # Create a temporary assignment containing the new decision
    temp_assignment = dict(assignment)
    temp_assignment[variable] = value

    new_domains = {}

    for var in problem.variables:

        # Already assigned variables keep their current domain
        if var in assignment or var == variable:
            new_domains[var] = domains[var][:]
            continue

        # Keep only values that remain consistent
        pruned_values = []

        for candidate in domains[var]:
            if is_consistent(problem, temp_assignment, var, candidate):
                pruned_values.append(candidate)

        # Empty domain means this branch can never succeed
        if not pruned_values:
            return None

        new_domains[var] = pruned_values

    return new_domains

def ac3(problem: CSPProblem, domains: dict[str, list[Rect]]) -> dict[str, list[Rect]] | None:
    """
    Optional AC-3 preprocessing. Return reduced domains, or None if
    inconsistency is detected.
    """
    # Work on a copy to avoid modifying the original domains
    new_domains = {var: list(values) for var, values in domains.items()}

    # Build the initial queue of binary constraint arcs
    queue = deque()

    for constraint in problem.constraints:
        if len(constraint.variables) == 2:
            x, y = constraint.variables
            queue.append((x, y))
            queue.append((y, x))

    def revise(x: str, y: str) -> bool:
        """
        Remove values from domain[x] that have no supporting value
        in domain[y].
        """

        relevant_constraints = [
            c for c in problem.constraints
            if set(c.variables) == {x, y}
        ]

        if not relevant_constraints:
            return False

        constraint = relevant_constraints[0]

        revised = False
        values_to_remove = []

        for vx in new_domains[x]:

            supported = False

            for vy in new_domains[y]:
                temp_assignment = {x: vx, y: vy}

                if constraint_is_satisfied(
                    problem,
                    constraint,
                    temp_assignment
                ):
                    supported = True
                    break

            if not supported:
                values_to_remove.append(vx)

        if values_to_remove:
            revised = True

            new_domains[x] = [
                value
                for value in new_domains[x]
                if value not in values_to_remove
            ]

        return revised

    while queue:

        x, y = queue.popleft()

        if revise(x, y):

            # Empty domain means the CSP is inconsistent
            if not new_domains[x]:
                return None

            # Recheck neighboring arcs
            for z in problem.variables:

                if z == x or z == y:
                    continue

                if any(
                    set(c.variables) == {x, z}
                    for c in problem.constraints
                ):
                    queue.append((z, x))

    return new_domains
