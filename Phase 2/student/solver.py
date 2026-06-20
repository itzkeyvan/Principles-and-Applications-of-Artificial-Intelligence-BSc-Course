from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment, Rect
from planforge.core.engine import SolverContext
from .consistency import is_consistent
from .heuristics import select_unassigned_variable, order_domain_values

# BONUS FEATURES TOGGLE
# Set BONUS_ENABLED = True to enable inference (forward_check, AC-3) and
# multi‑solution search (score_assignment). Set to False to run only the
# required part (stops after first solution, no pruning).
BONUS_ENABLED = True   # change to False to disable bonus features


# -----------------------------------------------------------------------------
# Optional inference imports (forward_check, ac3)
# These are only used if BONUS_ENABLED is True and the functions are defined.
if BONUS_ENABLED:
    try:
        from .inference import forward_check, ac3
        INFERENCE_AVAILABLE = True
    except (ImportError, NotImplementedError):
        INFERENCE_AVAILABLE = False
        forward_check = None
        ac3 = None
else:
    INFERENCE_AVAILABLE = False
    forward_check = None
    ac3 = None
# -----------------------------------------------------------------------------    

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
      2) optionally run ac3(problem, domains)   (bonus)
      3) call your recursive backtrack(...)
      4) return ctx.best_assignment, or None if no solution was found
    """
    # Copy the domains so we don't mutate the original problem
    domains = ctx.copy_domains()

    # -------------------------------------------------------------------------
    # BONUS: AC-3 preprocessing
    # If enabled and available, run AC-3 to reduce domains before search.
    if BONUS_ENABLED and INFERENCE_AVAILABLE and ac3 is not None:
        try:
            before_ac3 = ctx.domain_size(domains)
            reduced = ac3(problem, domains)
            if reduced is None:
                return None   # inconsistency detected
            after_ac3 = ctx.domain_size(reduced)
            ctx.on_prune(before_ac3, after_ac3)
            domains = reduced
        except NotImplementedError:
            pass   # fallback to original domains
    # -------------------------------------------------------------------------

    # Start recursive search
    backtrack(problem, {}, domains, ctx)

    # After search, return the best assignment (if any) stored in ctx
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
    ctx.on_node()           # Node count
    if ctx.should_stop:
        return
    
    # If all rooms are placed, we have a full solution.
    if is_complete(problem, assignment):
        ctx.on_solution(assignment)        # Framework validates and records answers
        # ---------------------------------------------------------------------
        # Required part: stop after first solution.
        # Bonus part: continue searching for better solutions.
        # ---------------------------------------------------------------------
        if not BONUS_ENABLED:
            return
        # If bonus is enabled, we do NOT return; we let the caller continue.
        # However, we must unwind to allow other branches to be explored.
        # The function will return to the caller (which will then try other values).
        # So we simply return without doing anything else.
        return

    # Step 6: MRV: choose the variable with fewest remaining consistent values
    # In the backtrack function, instead of the original for loop, we use this for MRV (Step 6):
    # MRV causes variables with smaller ranges to be selected first, so that invalid values are removed from the domain earlier
    var = select_unassigned_variable(problem, assignment, domains)

    # Tell the visualizer which room we're picking next
    ctx.on_select_variable(var, assignment)

    # Step 7: LCV (LCV heuristic): try values that leave more options for other variables first
    for value in order_domain_values(problem, var, assignment, domains):
        ctx.on_assignment_tried()
        ctx.on_consistency_check()

        if is_consistent(problem, assignment, var, value):
            assignment[var] = value

            # Record this placement so the visual mode can animate it
            ctx.on_assign(var, value, assignment)

            # -----------------------------------------------------------------
            # BONUS: Forward checking
            # If enabled and available, prune domains for the recursive call.
            if BONUS_ENABLED and INFERENCE_AVAILABLE and forward_check is not None:
                try:
                    before_fc = ctx.domain_size(domains)
                    pruned_domains = forward_check(problem, var, value, assignment, domains)
                    if pruned_domains is None:
                        # Pruning caused an empty domain → skip this branch
                        assignment.pop(var, None)
                        ctx.on_unassign(var, assignment)
                        continue
                    after_fc = ctx.domain_size(pruned_domains)
                    ctx.on_prune(before_fc, after_fc)
                    # Recursively continue the search with pruned domains
                    backtrack(problem, assignment, pruned_domains, ctx)
                except NotImplementedError:
                    # Fallback: use original domains
                    backtrack(problem, assignment, domains, ctx)
            else:
                # No forward checking: use original domains
                backtrack(problem, assignment, domains, ctx)
            # -----------------------------------------------------------------

            # Undo the choice before trying something else
            assignment.pop(var, None)

            # Update the visualizer to show that we're stepping back
            ctx.on_unassign(var, assignment)

            # Stop cleanly if the framework limit was reached
            if ctx.should_stop:
                ctx.on_backtrack()
                return

            # -----------------------------------------------------------------
            # Required part: stop after the first valid solution found.
            # Bonus part: continue searching for better solutions.
            # -----------------------------------------------------------------
            if not BONUS_ENABLED:
                # A valid solution was found deeper in the tree, so we can finish this search branch
                if ctx.best_assignment is not None:
                    ctx.on_backtrack()   # (optional) record that we are unwinding from a successful branch
                    return

    # No value worked for this variable, so this branch ends here
    ctx.on_backtrack()

def is_complete(problem: CSPProblem, assignment: Assignment) -> bool:
    """Return True iff every variable has a value."""
    return all(var in assignment for var in problem.variables)