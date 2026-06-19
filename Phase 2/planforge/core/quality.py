from __future__ import annotations
from .models import CSPProblem, Assignment
from .validator import validate_assignment
from .geometry import (
    used_area, aspect_ratio, touches_boundary, shared_wall_length,
    manhattan_rect_distance, distance_to_point, bounding_box,
    is_connected_layout, adjacent
)


def _find_room(assignment: Assignment, keyword: str):
    keyword = keyword.lower()
    for name, rect in assignment.items():
        if keyword in name.lower():
            return rect
    return None


def _rooms_matching(assignment: Assignment, *keywords: str):
    keys = tuple(k.lower() for k in keywords)
    return [(name, rect) for name, rect in assignment.items() if any(k in name.lower() for k in keys)]


def _norm_distance_to_entrance(problem: CSPProblem, rect) -> float:
    max_d = max(1.0, problem.width + problem.height)
    return min(1.0, distance_to_point(rect, problem.entrance) / max_d)


def layout_quality_score(problem: CSPProblem, assignment: Assignment | None) -> tuple[float, list[str]]:
    """
    Framework-owned quality score in [0, 100].

    Validity and quality are separate. A basic solution only needs to satisfy
    hard constraints; an advanced solution should improve coverage, circulation,
    zoning, daylight, room proportions and architectural adjacency.
    """
    if assignment is None:
        return 0.0, ["No assignment returned"]
    ok, errors = validate_assignment(problem, assignment)
    if not ok:
        return 0.0, errors

    floor_area = problem.width * problem.height
    used = used_area(list(assignment.values()))
    coverage = used / float(floor_area)
    notes: list[str] = []
    score = 0.0

    # 32 pts: efficient use of area. Full coverage is not required for validity,
    # but it is the strongest soft objective for advanced submissions.
    coverage_pts = 32.0 * min(1.0, coverage)
    score += coverage_pts
    if coverage >= 0.999:
        notes.append("Coverage: excellent — no unused cells")
    elif coverage >= 0.95:
        notes.append(f"Coverage: very good ({coverage:.1%})")
    elif coverage >= 0.85:
        notes.append(f"Coverage: acceptable but improvable ({coverage:.1%})")
    else:
        notes.append(f"Coverage: low ({coverage:.1%})")

    living = _find_room(assignment, "living")
    kitchen = _find_room(assignment, "kitchen")
    bathroom = _find_room(assignment, "bath")
    hall = _find_room(assignment, "hall")
    balcony = _find_room(assignment, "balcony")
    bedrooms = _rooms_matching(assignment, "bedroom")

    # 24 pts: circulation and access. Real apartment plans should not force
    # people through a bedroom to reach the bathroom; entry should lead to hall/living.
    circ = 0.0
    if hall is not None:
        circ += 5.0 * (1.0 - _norm_distance_to_entrance(problem, hall))
    if living is not None:
        circ += 4.0 * (1.0 - _norm_distance_to_entrance(problem, living))
    if hall is not None and living is not None and adjacent(hall, living):
        circ += 4.0
    if bathroom is not None:
        if hall is not None and adjacent(bathroom, hall):
            circ += 7.0
            notes.append("Bathroom access: excellent — directly connected to Hall")
        elif living is not None and adjacent(bathroom, living):
            circ += 4.0
            notes.append("Bathroom access: acceptable — reachable from Living")
        else:
            bedroom_adj = any(adjacent(bathroom, r) for _, r in bedrooms)
            if bedroom_adj:
                circ -= 6.0
                notes.append("Bathroom access: poor — bedroom-side access")
            else:
                notes.append("Bathroom access: weak — not tied to public circulation")
    if is_connected_layout(assignment):
        circ += 4.0
        notes.append("Connectivity: rooms form one connected layout")
    else:
        notes.append("Connectivity: disconnected room graph")
    score += max(0.0, min(24.0, circ))

    # 14 pts: public/private zoning. Bedrooms should be farther from the entry;
    # living/kitchen should form the public zone.
    zoning = 0.0
    if bedrooms:
        zoning += 7.0 * sum(_norm_distance_to_entrance(problem, r) for _, r in bedrooms) / len(bedrooms)
    if living is not None and kitchen is not None and adjacent(living, kitchen):
        zoning += 4.0
    if kitchen is not None and bathroom is not None and not adjacent(kitchen, bathroom):
        zoning += 3.0
    score += min(14.0, zoning)

    # 10 pts: daylight/exterior access for main rooms.
    main_rooms = _rooms_matching(assignment, "living", "bedroom", "kitchen", "balcony", "office", "study")
    if main_rooms:
        daylight_ratio = sum(1 for _, r in main_rooms if touches_boundary(r, problem.width, problem.height)) / len(main_rooms)
        score += 10.0 * daylight_ratio
        notes.append(f"Daylight: {daylight_ratio:.0%} of main rooms touch exterior")

    # 8 pts: non-elongated room shapes.
    if assignment:
        shape_ratio = sum(max(0.0, 1.0 - max(0.0, aspect_ratio(r) - 2.0) / 1.5) for r in assignment.values()) / len(assignment)
        score += 8.0 * shape_ratio

    # 8 pts: architectural adjacency and service logic.
    pref = 0.0
    if living is not None and kitchen is not None:
        pref += min(4.0, shared_wall_length(living, kitchen) * 0.9)
    if kitchen is not None and balcony is not None and adjacent(kitchen, balcony):
        pref += 1.5
    if living is not None and balcony is not None and adjacent(living, balcony):
        pref += 1.5
    if bathroom is not None and kitchen is not None:
        pref += min(1.0, manhattan_rect_distance(bathroom, kitchen) * 0.25)
    score += min(8.0, pref)

    # 4 pts: compactness and avoiding scattered islands/holes inside the bounding box.
    box = bounding_box(list(assignment.values()))
    wasted_inside_box = max(0, box.area - used)
    score += max(0.0, 4.0 - wasted_inside_box * 0.45)

    return round(max(0.0, min(100.0, score)), 2), notes
