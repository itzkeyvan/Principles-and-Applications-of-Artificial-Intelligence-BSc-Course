from __future__ import annotations
from .models import CSPProblem, Assignment
from .geometry import inside_boundary, overlaps, used_area, is_connected_layout, aspect_ratio
from .constraints import constraint_is_satisfied

def validate_assignment(problem: CSPProblem, assignment: Assignment) -> tuple[bool, list[str]]:
    errors: list[str] = []
    missing = [v for v in problem.variables if v not in assignment]
    if missing:
        errors.append(f'Missing variables: {missing}')
        return False, errors
    for v, r in assignment.items():
        if not inside_boundary(r, problem.width, problem.height):
            errors.append(f'{v} is outside boundary')
        spec = problem.room_specs[v]
        if not (spec.min_area <= r.area <= spec.max_area):
            errors.append(f'{v} area {r.area} outside [{spec.min_area}, {spec.max_area}]')
        if aspect_ratio(r) > spec.max_aspect_ratio + 1e-9:
            errors.append(f'{v} aspect ratio too high')
    vs = list(assignment)
    for i, a in enumerate(vs):
        for b in vs[i+1:]:
            if overlaps(assignment[a], assignment[b]):
                errors.append(f'{a} overlaps {b}')
    for c in problem.constraints:
        if not constraint_is_satisfied(problem, c, assignment):
            errors.append(f'Constraint failed: {c.type} {c.variables} {c.params}')
    coverage = used_area(list(assignment.values())) / float(problem.width * problem.height)
    if coverage < problem.min_coverage_ratio:
        errors.append(f'Coverage ratio too low: {coverage:.2f} < {problem.min_coverage_ratio:.2f}')
    if problem.require_connected and not is_connected_layout(assignment):
        errors.append('Layout adjacency graph is disconnected')
    return (len(errors) == 0, errors)
