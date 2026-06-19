from __future__ import annotations
from planforge.core.models import CSPProblem, Assignment

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
    raise NotImplementedError('TODO: implement score_assignment() in student/scoring.py')
