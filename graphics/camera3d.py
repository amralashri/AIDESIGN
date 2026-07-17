from __future__ import annotations

from dataclasses import dataclass, field
from math import radians, tan
import numpy as np


def normalize(vector: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    vector = np.asarray(vector, dtype=float)
    length = float(np.linalg.norm(vector))
    if length <= 1.0e-12:
        if fallback is None:
            raise ValueError("Cannot normalize a zero vector.")
        return np.asarray(fallback, dtype=float).copy()
    return vector / length


def rotate_vector(vector: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues rotation."""
    axis = normalize(axis)
    vector = np.asarray(vector, dtype=float)
    c = np.cos(angle)
    s = np.sin(angle)
    return (
        vector*c
        + np.cross(axis, vector)*s
        + axis*np.dot(axis, vector)*(1.0-c)
    )


@dataclass(slots=True)
class RevitOrbitCamera:
    """
    Perspective orbit camera with a movable pivot.

    - The camera orbits around ``target`` rather than a hard-coded origin.
    - Panning moves both eye and target.
    - Zoom changes camera distance.
    - Default isometric view keeps global Z upright.
    - Pitch is limited just before the vertical singularity, preventing the
      upside-down default and unexpected view inversion.
    """
    target: np.ndarray = field(default_factory=lambda: np.zeros(3))
    eye: np.ndarray = field(default_factory=lambda: np.array([12.0,-12.0,9.0]))
    up: np.ndarray = field(default_factory=lambda: np.array([0.0,0.0,1.0]))
    field_of_view_degrees: float = 38.0
    near_clip: float = 0.01
    far_clip: float = 1.0e8

    def copy(self) -> "RevitOrbitCamera":
        return RevitOrbitCamera(
            self.target.copy(), self.eye.copy(), self.up.copy(),
            self.field_of_view_degrees, self.near_clip, self.far_clip,
        )

    @property
    def distance(self) -> float:
        return float(np.linalg.norm(self.eye-self.target))

    def basis(self) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
        forward = normalize(
            self.target-self.eye,
            np.array([0.0,1.0,0.0]),
        )
        right = normalize(
            np.cross(forward, self.up),
            np.array([1.0,0.0,0.0]),
        )
        true_up = normalize(np.cross(right, forward))
        return right, true_up, forward

    def set_isometric(self, distance: float | None = None) -> None:
        if distance is None:
            distance = max(self.distance, 10.0)
        # South-east isometric: X right, Y recedes left, Z remains upward.
        direction = normalize(np.array([1.25,-1.25,0.90]))
        self.eye = self.target + direction*distance
        self.up = np.array([0.0,0.0,1.0])

    def set_top(self, distance: float | None = None) -> None:
        if distance is None:
            distance = max(self.distance,10.0)
        self.eye = self.target + np.array([0.0,0.0,distance])
        self.up = np.array([0.0,1.0,0.0])

    def set_front(self, distance: float | None = None) -> None:
        if distance is None:
            distance = max(self.distance,10.0)
        self.eye = self.target + np.array([0.0,-distance,0.0])
        self.up = np.array([0.0,0.0,1.0])

    def set_right(self, distance: float | None = None) -> None:
        if distance is None:
            distance = max(self.distance,10.0)
        self.eye = self.target + np.array([distance,0.0,0.0])
        self.up = np.array([0.0,0.0,1.0])

    def orbit(self, dx_pixels: float, dy_pixels: float) -> None:
        offset = self.eye-self.target
        distance = max(float(np.linalg.norm(offset)),1.0e-6)

        # Horizontal movement is around the fixed global vertical, as in Revit.
        yaw = -dx_pixels*0.006
        offset = rotate_vector(offset, np.array([0.0,0.0,1.0]), yaw)

        # Vertical movement is around the current screen-right axis.
        forward = normalize(-offset)
        right = normalize(
            np.cross(forward, np.array([0.0,0.0,1.0])),
            np.array([1.0,0.0,0.0]),
        )
        pitch = -dy_pixels*0.006
        proposed = rotate_vector(offset, right, pitch)

        # Keep global Z upward and avoid passing through the pole.
        proposed_forward = normalize(-proposed)
        vertical_alignment = abs(float(np.dot(
            proposed_forward, np.array([0.0,0.0,1.0])
        )))
        if vertical_alignment < 0.985:
            offset = proposed

        self.eye = self.target + normalize(offset)*distance
        self.up = np.array([0.0,0.0,1.0])

    def pan(self, dx_pixels: float, dy_pixels: float, viewport_height: int) -> None:
        right, true_up, _ = self.basis()
        world_per_pixel = (
            2.0*self.distance
            * tan(radians(self.field_of_view_degrees)/2.0)
            / max(float(viewport_height),1.0)
        )
        translation = (
            -right*dx_pixels*world_per_pixel
            + true_up*dy_pixels*world_per_pixel
        )
        self.eye += translation
        self.target += translation

    def zoom(self, wheel_steps: float) -> None:
        direction = normalize(self.eye-self.target)
        factor = 0.86**wheel_steps
        new_distance = float(np.clip(
            self.distance*factor, 0.05, 1.0e7
        ))
        self.eye = self.target + direction*new_distance

    def set_pivot(self, pivot: np.ndarray, preserve_eye: bool = True) -> None:
        pivot = np.asarray(pivot,dtype=float)
        if preserve_eye:
            self.target = pivot
            if self.distance < 0.05:
                self.eye = pivot + np.array([1.0,-1.0,0.8])
        else:
            offset = self.eye-self.target
            self.target = pivot
            self.eye = pivot+offset

    def project(
        self,
        point: np.ndarray,
        width: int,
        height: int,
    ) -> tuple[float,float,float,bool]:
        right, true_up, forward = self.basis()
        relative = np.asarray(point,dtype=float)-self.eye
        x = float(np.dot(relative,right))
        y = float(np.dot(relative,true_up))
        depth = float(np.dot(relative,forward))
        visible = self.near_clip < depth < self.far_clip
        focal = (
            max(float(height),1.0)
            / (2.0*tan(radians(self.field_of_view_degrees)/2.0))
        )
        safe_depth = max(depth,self.near_clip)
        sx = width/2.0 + focal*x/safe_depth
        sy = height/2.0 - focal*y/safe_depth
        return sx,sy,depth,visible

    def fit_points(
        self,
        points: list[np.ndarray],
        aspect_ratio: float = 1.0,
        padding: float = 1.25,
    ) -> None:
        if not points:
            self.target = np.zeros(3)
            self.set_isometric(20.0)
            return
        array = np.vstack(points)
        minimum = array.min(axis=0)
        maximum = array.max(axis=0)
        center = (minimum+maximum)/2.0
        radius = max(float(np.linalg.norm(maximum-minimum))/2.0,1.0)
        self.target = center

        vertical_fov = radians(self.field_of_view_degrees)
        horizontal_fov = 2.0*np.arctan(
            np.tan(vertical_fov/2.0)*max(aspect_ratio,0.1)
        )
        limiting_fov = min(vertical_fov,horizontal_fov)
        distance = padding*radius/max(np.sin(limiting_fov/2.0),0.05)
        direction = normalize(self.eye-self.target, np.array([1.25,-1.25,0.9]))
        self.eye = self.target + direction*distance

    def ray_from_screen(
        self,
        screen_x: float,
        screen_y: float,
        width: int,
        height: int,
    ) -> tuple[np.ndarray,np.ndarray]:
        right,true_up,forward=self.basis()
        focal = (
            max(float(height),1.0)
            / (2.0*tan(radians(self.field_of_view_degrees)/2.0))
        )
        x=(screen_x-width/2.0)/focal
        y=-(screen_y-height/2.0)/focal
        direction=normalize(forward+x*right+y*true_up)
        return self.eye.copy(),direction
