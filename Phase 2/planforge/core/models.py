from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

@dataclass(frozen=True)
class RoomSpec:
    name: str
    min_area: int
    max_area: int
    min_w: int = 1
    max_w: int | None = None
    min_h: int = 1
    max_h: int | None = None
    needs_exterior: bool = False
    max_aspect_ratio: float = 3.0

@dataclass(frozen=True)
class Constraint:
    type: str
    variables: tuple[str, ...]
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class CSPProblem:
    width: int
    height: int
    entrance: tuple[int, int]
    variables: list[str]
    room_specs: dict[str, RoomSpec]
    domains: dict[str, list[Rect]]
    constraints: list[Constraint]
    soft_weights: dict[str, float] = field(default_factory=dict)
    min_coverage_ratio: float = 0.82
    require_connected: bool = True

Assignment = dict[str, Rect]
