from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment
from planforge.core.geometry import (used_area,aspect_ratio,touches_boundary,shared_wall_length,distance_to_point, bounding_box,adjacent)
# -----------------------------------------------------------------------------
# STUDENT TODO FILE
# Bonus / advanced: soft constraints and optimization objective.
# The framework engine uses this score to choose the best valid layout among
# complete assignments it finds.
# -----------------------------------------------------------------------------


def score_assignment(problem: CSPProblem, assignment: Assignment) -> float:
    """
    Compute a quality score for a complete VALID floor plan.
    Recommended range: 0 to 100. Higher score = better layout.
    Full coverage is NOT required for a valid solution; it is a soft objective for stronger solutions.

    Suggested soft factors:
      - living room near entrance
      - bedrooms far from entrance
      - longer shared wall between kitchen and living
      - non-elongated room shapes
      - better daylight / exterior access
      - bathroom accessible from hall/public circulation
      - bathroom not hidden behind a bedroom
      - bathroom farther from kitchen
      - compact overall plan
      - higher apartment coverage ratio / less wasted area
    """
    if assignment is None:
        return 0.0

    if len(assignment) != len(problem.variables):
        return 0.0

    floor_area = problem.width * problem.height
    used = used_area(list(assignment.values()))

    # 1) Coverage
    # Reward solutions that use more of the available apartment.
    coverage_ratio = used / floor_area
    score = 30.0 * min(1.0, coverage_ratio)

    # 2) Room shape quality
    # Penalize very elongated rooms.
    shape_score = 0.0

    for rect in assignment.values():
        ratio = aspect_ratio(rect)

        room_quality = max(
            0.0,
            1.0 - (ratio - 1.0) / 2.0
        )

        shape_score += room_quality

    shape_score /= max(1, len(assignment))

    score += 10.0 * shape_score

    # 3) Exterior access
    # Main rooms benefit from natural light.
    main_keywords = [
        "living",
        "bedroom",
        "kitchen",
        "office",
        "balcony"
    ]

    main_rooms = [
        room
        for room in problem.variables
        if any(k in room.lower() for k in main_keywords)
    ]

    if main_rooms:

        exterior_count = sum(
            1
            for room in main_rooms
            if touches_boundary(
                assignment[room],
                problem.width,
                problem.height
            )
        )

        score += (
            10.0 *
            exterior_count /
            len(main_rooms)
        )

    # 4) Entrance accessibility
    # Hall and living room should be reasonably close.
    entrance = problem.entrance

    hall = next(
        (v for v in problem.variables
         if "hall" in v.lower()),
        None
    )

    living = next(
        (v for v in problem.variables
         if "living" in v.lower()),
        None
    )

    max_distance = problem.width + problem.height

    if hall:

        distance = distance_to_point(
            assignment[hall],
            entrance
        )

        score += 8.0 * (
            1.0 - min(1.0, distance / max_distance)
        )

    if living:

        distance = distance_to_point(
            assignment[living],
            entrance
        )

        score += 7.0 * (
            1.0 - min(1.0, distance / max_distance)
        )

    # 5) Kitchen-Living relationship
    # Prefer direct adjacency and a longer shared wall.
    kitchen = next(
        (v for v in problem.variables
         if "kitchen" in v.lower()),
        None
    )

    if kitchen and living:

        if adjacent(
            assignment[kitchen],
            assignment[living]
        ):

            wall = shared_wall_length(
                assignment[kitchen],
                assignment[living]
            )

            score += min(8.0, wall * 0.8)

    # 6) Bathroom accessibility
    # Prefer bathroom connected to hall.
    bathroom = next(
        (v for v in problem.variables
         if "bath" in v.lower()),
        None
    )

    if bathroom and hall:

        if adjacent(
            assignment[bathroom],
            assignment[hall]
        ):
            score += 5.0

    # 7) Compactness
    # Penalize large empty gaps inside the bounding box.
    box = bounding_box(list(assignment.values()))

    wasted_area = max(
        0,
        box.area - used
    )

    score += max(
        0.0,
        5.0 - wasted_area * 0.4
    )

    # Keep the score in the expected range
    return max(0.0, min(100.0, score))