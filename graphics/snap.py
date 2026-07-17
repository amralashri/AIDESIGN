from __future__ import annotations
from dataclasses import dataclass
from math import hypot
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SnapResult:
    x: float
    y: float
    kind: str
    distance_pixels: float


class SnapEngine:
    def __init__(self, tolerance_pixels: float = 14.0) -> None:
        self.tolerance_pixels = tolerance_pixels

    def find(self, world_x: float, world_y: float, zoom: float,
             x_grids: Iterable[float], y_grids: Iterable[float],
             endpoints: Iterable[tuple[float,float]],
             midpoints: Iterable[tuple[float,float]]) -> SnapResult | None:
        candidates=[]
        for x,y in endpoints: candidates.append((x,y,"Endpoint"))
        for x,y in midpoints: candidates.append((x,y,"Midpoint"))
        for x in x_grids:
            for y in y_grids: candidates.append((x,y,"Grid"))
        best=None
        for x,y,kind in candidates:
            dp=hypot(x-world_x,y-world_y)*zoom
            if dp<=self.tolerance_pixels and (best is None or dp<best.distance_pixels):
                best=SnapResult(x,y,kind,dp)
        return best
