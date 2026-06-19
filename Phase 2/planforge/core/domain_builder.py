from __future__ import annotations
from .models import RoomSpec, Rect
from .geometry import aspect_ratio, touches_boundary

def _infer_needs_exterior(name: str) -> bool:
    key = name.lower()
    return any(tag in key for tag in ['bedroom', 'living', 'kitchen', 'balcony', 'office'])

def build_domains(width: int, height: int, specs: list[RoomSpec]) -> dict[str, list[Rect]]:
    domains: dict[str, list[Rect]] = {}
    for s in specs:
        vals: list[Rect] = []
        max_w = min(width, s.max_w or width)
        max_h = min(height, s.max_h or height)
        needs_exterior = s.needs_exterior or _infer_needs_exterior(s.name)
        for w in range(s.min_w, max_w + 1):
            for h in range(s.min_h, max_h + 1):
                area = w * h
                if not (s.min_area <= area <= s.max_area):
                    continue
                temp = Rect(0, 0, w, h)
                if aspect_ratio(temp) > s.max_aspect_ratio:
                    continue
                for x in range(0, width - w + 1):
                    for y in range(0, height - h + 1):
                        r = Rect(x, y, w, h)
                        if needs_exterior and not touches_boundary(r, width, height):
                            continue
                        vals.append(r)
        # Stable ordering: larger areas first, then less elongated, then near top-left.
        vals.sort(key=lambda r: (-r.area, aspect_ratio(r), r.y, r.x))
        domains[s.name] = vals
    return domains
