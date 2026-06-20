from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect
from planforge.core.engine import SolverContext
from .consistency import is_consistent

# -----------------------------------------------------------------------------
# STUDENT TODO FILE
# You MUST implement recursive backtracking here.
#
# The framework passes a SolverContext named `ctx` into solve(). Use it to record
# metadata and best solutions:
#   ctx.on_node()                 # once at the beginning of each backtrack node
#   ctx.on_assignment_tried()      # before trying a value
#   ctx.on_consistency_check()     # before/around is_consistent
#   ctx.on_prune(before, after)    # after forward checking / AC-3 pruning
#   ctx.on_solution(assignment)    # when assignment is complete
#   ctx.on_backtrack()             # when returning from a dead end / node
#   ctx.should_stop                # respect framework limits
# -----------------------------------------------------------------------------


def solve(problem: CSPProblem, ctx: SolverContext) -> Assignment | None:
    """
    Entry point called by the framework.

    Required behavior:
      1) copy domains from ctx.copy_domains()
      2) optionally run ac3(problem, domains)
      3) call your recursive backtrack(...)
      4) return ctx.best_assignment, or None if no solution was found
    """
    domains = ctx.copy_domains()
    backtrack(problem, {}, domains, ctx)
    return ctx.best_assignment


def backtrack(problem: CSPProblem, assignment: Assignment, domains: dict[str, list[Rect]], ctx: SolverContext) -> None:
    """
    Recursive backtracking search.

    This function should explore assignments and call ctx.on_solution(assignment)
    whenever a complete assignment is reached. ctx stores the best valid solution
    according to score_assignment().

    For the visual solver mode in the app, call ctx.on_select_variable(...),
    ctx.on_assign(...), and ctx.on_unassign(...) at the appropriate points.
    These calls do not change correctness; they only let the app animate the
    exact search path produced by your algorithm.
    """
    # We don't use MRV/LCV yet, we just take the first variable without a value
    if is_complete(problem, assignment):
        # In step 5, we add ctx.on_solution here
        return

    # Select the first variable without a value
    for var in problem.variables:
        if var not in assignment:
            break
    else:
        return  # Shouldn't happen.

    # Test all values ​​in order (no LCV)
    for value in domains[var]:
        if is_consistent(problem, assignment, var, value):
            assignment[var] = value
            backtrack(problem, assignment, domains, ctx)
            # If the answer is found, we will return.
            if ctx.best_assignment is not None:
                assignment.pop(var, None)
                return
            assignment.pop(var, None)

def is_complete(problem: CSPProblem, assignment: Assignment) -> bool:
    """Return True iff every variable has a value."""
    return all(var in assignment for var in problem.variables)
