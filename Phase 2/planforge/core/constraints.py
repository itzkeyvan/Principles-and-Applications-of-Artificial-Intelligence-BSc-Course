from __future__ import annotations
from .models import Constraint, CSPProblem, Assignment, Rect
from .geometry import adjacent, touches_boundary, touches_wall, manhattan_rect_distance, distance_to_point

def parse_constraint(raw: dict) -> Constraint:
    ctype = raw['type']
    if 'room' in raw:
        variables = (raw['room'],)
    elif 'a' in raw and 'b' in raw:
        variables = (raw['a'], raw['b'])
    else:
        variables = tuple(raw.get('variables', []))
    params = {k: v for k, v in raw.items() if k not in {'type', 'room', 'a', 'b', 'variables'}}
    return Constraint(ctype, variables, params)

def constraint_is_satisfied(problem: CSPProblem, c: Constraint, assignment: Assignment) -> bool:
    if any(v not in assignment for v in c.variables):
        return True
    t = c.type
    vars_ = c.variables
    if t == 'touches_boundary':
        return touches_boundary(assignment[vars_[0]], problem.width, problem.height)
    if t == 'touches_wall':
        return touches_wall(assignment[vars_[0]], c.params['wall'], problem.width, problem.height)
    if t == 'near_entrance':
        return distance_to_point(assignment[vars_[0]], problem.entrance) <= c.params.get('max_distance', 5)
    if t == 'far_from_entrance':
        return distance_to_point(assignment[vars_[0]], problem.entrance) >= c.params.get('min_distance', 4)
    a, b = assignment[vars_[0]], assignment[vars_[1]]
    if t == 'adjacent':
        return adjacent(a, b)
    if t == 'not_adjacent':
        return not adjacent(a, b)
    if t == 'near':
        return manhattan_rect_distance(a, b) <= c.params.get('max_distance', 2)
    if t == 'far':
        return manhattan_rect_distance(a, b) >= c.params.get('min_distance', 2)
    if t == 'larger_than':
        return a.area > b.area
    raise ValueError(f'Unknown constraint type: {t}')
