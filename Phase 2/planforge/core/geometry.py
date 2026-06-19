from __future__ import annotations
from collections import deque
from .models import Rect

def inside_boundary(r: Rect, width: int, height: int) -> bool:
    return r.x >= 0 and r.y >= 0 and r.x2 <= width and r.y2 <= height

def overlaps(a: Rect, b: Rect) -> bool:
    return not (a.x2 <= b.x or b.x2 <= a.x or a.y2 <= b.y or b.y2 <= a.y)

def adjacent(a: Rect, b: Rect) -> bool:
    vertical_touch = (a.x2 == b.x or b.x2 == a.x) and max(a.y, b.y) < min(a.y2, b.y2)
    horizontal_touch = (a.y2 == b.y or b.y2 == a.y) and max(a.x, b.x) < min(a.x2, b.x2)
    return vertical_touch or horizontal_touch

def shared_wall_length(a: Rect, b: Rect) -> int:
    if a.x2 == b.x or b.x2 == a.x:
        return max(0, min(a.y2, b.y2) - max(a.y, b.y))
    if a.y2 == b.y or b.y2 == a.y:
        return max(0, min(a.x2, b.x2) - max(a.x, b.x))
    return 0

def center(r: Rect) -> tuple[float, float]:
    return (r.x + r.w / 2.0, r.y + r.h / 2.0)

def manhattan_rect_distance(a: Rect, b: Rect) -> int:
    dx = max(0, max(a.x, b.x) - min(a.x2, b.x2))
    dy = max(0, max(a.y, b.y) - min(a.y2, b.y2))
    return dx + dy

def distance_to_point(r: Rect, p: tuple[int, int]) -> float:
    cx, cy = center(r)
    return abs(cx - p[0]) + abs(cy - p[1])

def touches_boundary(r: Rect, width: int, height: int) -> bool:
    return r.x == 0 or r.y == 0 or r.x2 == width or r.y2 == height

def touches_wall(r: Rect, wall: str, width: int, height: int) -> bool:
    wall = wall.lower()
    if wall == 'north': return r.y == 0
    if wall == 'south': return r.y2 == height
    if wall == 'west': return r.x == 0
    if wall == 'east': return r.x2 == width
    raise ValueError(f'Unknown wall: {wall}')

def aspect_ratio(r: Rect) -> float:
    longer, shorter = max(r.w, r.h), max(1, min(r.w, r.h))
    return longer / shorter

def bounding_box(rects: list[Rect]) -> Rect:
    min_x = min(r.x for r in rects)
    min_y = min(r.y for r in rects)
    max_x = max(r.x2 for r in rects)
    max_y = max(r.y2 for r in rects)
    return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

def used_area(rects: list[Rect]) -> int:
    return sum(r.area for r in rects)

def adjacency_graph(assignment: dict[str, Rect]) -> dict[str, set[str]]:
    g = {k: set() for k in assignment}
    keys = list(assignment)
    for i, a in enumerate(keys):
        for b in keys[i+1:]:
            if adjacent(assignment[a], assignment[b]):
                g[a].add(b)
                g[b].add(a)
    return g

def is_connected_layout(assignment: dict[str, Rect]) -> bool:
    if not assignment:
        return True
    g = adjacency_graph(assignment)
    start = next(iter(g))
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in g[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return len(seen) == len(g)
