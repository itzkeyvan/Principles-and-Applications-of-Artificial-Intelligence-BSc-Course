from __future__ import annotations
from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Callable

from .models import CSPProblem, Assignment, Rect
from .validator import validate_assignment
from .quality import layout_quality_score


@dataclass
class SolverReport:
    status: str = "not_started"
    runtime_sec: float = 0.0
    nodes: int = 0
    backtracks: int = 0
    assignments_tried: int = 0
    consistency_checks: int = 0
    solutions_seen: int = 0
    pruned_values: int = 0
    best_score: float | None = None
    layout_score: float | None = None
    max_layout_score: float = 100.0
    validation_errors: list[str] | None = None
    error: str | None = None
    stopped_by_limit: bool = False
    instrumentation_warnings: list[str] | None = None
    trace_events: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SolverContext:
    """
    Instrumentation object passed to the student-owned backtracking solver.

    Students implement recursive backtracking themselves, but call context
    methods so the framework can record metadata and keep the best valid
    assignment behind the scenes.
    """

    def __init__(
        self,
        problem: CSPProblem,
        score_fn: Callable[[CSPProblem, Assignment], float] | None = None,
        *,
        max_solutions: int = 250,
        max_nodes: int = 100_000,
        trace: bool = False,
        max_trace_events: int = 1800,
    ):
        self.problem = problem
        self.score_fn = score_fn
        self.max_solutions = max_solutions
        self.max_nodes = max_nodes
        self.trace_enabled = trace
        self.max_trace_events = max_trace_events
        self.report = SolverReport(instrumentation_warnings=[], trace_events=[] if trace else None)
        self.best_assignment: Assignment | None = None
        self.best_score = float("-inf")

    @property
    def should_stop(self) -> bool:
        if self.report.nodes >= self.max_nodes or self.report.solutions_seen >= self.max_solutions:
            self.report.stopped_by_limit = True
            return True
        return False


    def _assignment_snapshot(self, assignment: Assignment | None) -> dict[str, tuple[int, int, int, int]]:
        if not assignment:
            return {}
        return {name: rect.as_tuple() for name, rect in assignment.items()}

    def _trace(self, event_type: str, assignment: Assignment | None = None, **payload: Any) -> None:
        if not self.trace_enabled or self.report.trace_events is None:
            return
        if len(self.report.trace_events) >= self.max_trace_events:
            return
        item: dict[str, Any] = {
            "type": event_type,
            "nodes": self.report.nodes,
            "backtracks": self.report.backtracks,
            "solutions_seen": self.report.solutions_seen,
            "pruned_values": self.report.pruned_values,
            "assignment": self._assignment_snapshot(assignment),
        }
        item.update(payload)
        self.report.trace_events.append(item)

    def on_select_variable(self, variable: str, assignment: Assignment | None = None) -> None:
        self._trace("select", assignment, variable=variable)

    def on_assign(self, variable: str, value: Rect, assignment: Assignment) -> None:
        self._trace("assign", assignment, variable=variable, value=value.as_tuple())

    def on_unassign(self, variable: str, assignment: Assignment | None = None) -> None:
        self._trace("unassign", assignment, variable=variable)

    def copy_domains(self) -> dict[str, list[Rect]]:
        return {v: list(vals) for v, vals in self.problem.domains.items()}

    def domain_size(self, domains: dict[str, list[Rect]]) -> int:
        return sum(len(vals) for vals in domains.values())

    def on_node(self) -> None:
        self.report.nodes += 1
        if self.report.nodes >= self.max_nodes:
            self.report.stopped_by_limit = True

    def on_backtrack(self) -> None:
        self.report.backtracks += 1
        self._trace("backtrack")

    def on_assignment_tried(self) -> None:
        self.report.assignments_tried += 1

    def on_consistency_check(self) -> None:
        self.report.consistency_checks += 1

    def on_prune(self, before: int | None = None, after: int | None = None, count: int | None = None, assignment: Assignment | None = None) -> None:
        if count is None:
            count = max(0, int((before or 0) - (after or 0)))
        count = max(0, int(count))
        self.report.pruned_values += count
        if count:
            self._trace("prune", assignment, count=count)

    def on_solution(self, assignment: Assignment) -> bool:
        ok, errors = validate_assignment(self.problem, assignment)
        if not ok:
            self.report.validation_errors = errors
            return False
        self.report.solutions_seen += 1
        score = 0.0
        if self.score_fn is not None:
            try:
                score = float(self.score_fn(self.problem, assignment))
            except NotImplementedError:
                score = 0.0
        self._trace("solution", assignment, score=score)
        if score > self.best_score:
            self.best_score = score
            self.best_assignment = dict(assignment)
            self.report.best_score = score
            self.report.layout_score, _ = layout_quality_score(self.problem, assignment)
        return True

    def warn(self, message: str) -> None:
        if self.report.instrumentation_warnings is None:
            self.report.instrumentation_warnings = []
        self.report.instrumentation_warnings.append(message)


def solve_with_report(problem: CSPProblem, *, max_solutions: int = 250, max_nodes: int = 100_000, trace: bool = False, max_trace_events: int = 1800) -> tuple[Assignment | None, SolverReport]:
    """
    Controlled runner for the student-owned backtracking solver.

    The student implements student/solver.py and receives a SolverContext. The
    runner does not implement search itself; it loads the student solver, times
    it, catches errors, and builds the final report.
    """
    start = perf_counter()
    try:
        from student.solver import solve as student_solve
        from student.scoring import score_assignment
    except Exception as exc:
        report = SolverReport(status="import_error", error=f"{type(exc).__name__}: {exc}")
        report.runtime_sec = round(perf_counter() - start, 6)
        return None, report

    ctx = SolverContext(problem, score_assignment, max_solutions=max_solutions, max_nodes=max_nodes, trace=trace, max_trace_events=max_trace_events)
    ctx.report.status = "running"
    try:
        returned_assignment = student_solve(problem, ctx)
    except NotImplementedError as exc:
        ctx.report.status = "not_implemented"
        ctx.report.error = str(exc)
        ctx.report.runtime_sec = round(perf_counter() - start, 6)
        return None, ctx.report
    except Exception as exc:
        ctx.report.status = "runtime_error"
        ctx.report.error = f"{type(exc).__name__}: {exc}"
        ctx.report.runtime_sec = round(perf_counter() - start, 6)
        return None, ctx.report

    assignment = ctx.best_assignment
    if assignment is None and returned_assignment is not None:
        ok, errors = validate_assignment(problem, returned_assignment)
        if ok:
            ctx.warn("Returned a valid assignment but did not call ctx.on_solution(); metadata/score may be incomplete.")
            assignment = dict(returned_assignment)
            ctx.best_assignment = assignment
            try:
                score = float(score_assignment(problem, assignment))
            except Exception:
                score = 0.0
            ctx.best_score = score
            ctx.report.best_score = score
            ctx.report.layout_score, _ = layout_quality_score(problem, assignment)
        else:
            ctx.report.validation_errors = errors

    ctx.report.runtime_sec = round(perf_counter() - start, 6)
    if assignment is None:
        ctx.report.status = "no_solution"
        ctx.report.best_score = None
        return None, ctx.report

    ok, errors = validate_assignment(problem, assignment)
    ctx.report.validation_errors = errors
    ctx.report.best_score = ctx.best_score if ctx.best_score != float("-inf") else None
    ctx.report.layout_score, _ = layout_quality_score(problem, assignment)
    ctx.report.status = "valid" if ok else "invalid"
    return assignment if ok else None, ctx.report
