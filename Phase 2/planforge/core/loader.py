from __future__ import annotations
import json
from pathlib import Path
from .models import CSPProblem, RoomSpec
from .domain_builder import build_domains
from .constraints import parse_constraint

def load_problem(path: str | Path) -> CSPProblem:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    specs = [RoomSpec(
        name=r['name'],
        min_area=r['minArea'],
        max_area=r['maxArea'],
        min_w=r.get('minW', 1),
        max_w=r.get('maxW'),
        min_h=r.get('minH', 1),
        max_h=r.get('maxH'),
        needs_exterior=r.get('needsExterior', False),
        max_aspect_ratio=r.get('maxAspectRatio', 3.0),
    ) for r in data['rooms']]
    domains = build_domains(data['width'], data['height'], specs)
    return CSPProblem(
        width=data['width'],
        height=data['height'],
        entrance=tuple(data.get('entrance', [0, data['height'] - 1])),
        variables=[s.name for s in specs],
        room_specs={s.name: s for s in specs},
        domains=domains,
        constraints=[parse_constraint(c) for c in data.get('constraints', [])],
        soft_weights=data.get('softWeights', {}),
        min_coverage_ratio=data.get('minCoverageRatio', 0.82),
        require_connected=data.get('requireConnected', True),
    )
