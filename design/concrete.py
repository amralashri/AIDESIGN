from __future__ import annotations

from dataclasses import dataclass, field
from math import pi

import numpy as np

from analysis.postprocessing import dominant_curve
from analysis.results import AnalysisResult
from model.project import ProjectModel


@dataclass(slots=True)
class ConcreteDesignSettings:
    concrete_strength_mpa: float = 30.0
    steel_yield_mpa: float = 420.0
    strength_reduction_factor: float = 0.90
    beam_cover_mm: float = 40.0
    slab_cover_mm: float = 25.0
    beam_bar_diameter_mm: float = 20.0
    slab_bar_diameter_mm: float = 12.0
    minimum_reinforcement_ratio: float = 0.0018
    maximum_slab_spacing_mm: float = 300.0
    minimum_slab_spacing_mm: float = 75.0


@dataclass(slots=True)
class BeamDesignResult:
    frame_id: int
    governing_moment_knm: float
    required_area_mm2: float
    provided_bar_count: int
    bar_diameter_mm: float
    label: str


@dataclass(slots=True)
class SlabDesignResult:
    area_id: int
    mx_knm_per_m: float
    my_knm_per_m: float
    as_x_mm2_per_m: float
    as_y_mm2_per_m: float
    spacing_x_mm: float
    spacing_y_mm: float
    bar_diameter_mm: float
    label_x: str
    label_y: str


@dataclass(slots=True)
class ConcreteDesignResult:
    settings: ConcreteDesignSettings
    beams: dict[int, BeamDesignResult] = field(default_factory=dict)
    slabs: dict[int, SlabDesignResult] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _required_steel_area(
    moment_knm: float,
    effective_depth_m: float,
    fy_mpa: float,
    phi: float,
) -> float:
    if effective_depth_m <= 0.0:
        return 0.0
    fy_kn_per_m2 = fy_mpa * 1000.0
    lever_arm = 0.90 * effective_depth_m
    as_m2 = abs(moment_knm) / max(
        phi * fy_kn_per_m2 * lever_arm, 1.0e-12
    )
    return as_m2 * 1.0e6


def _bar_area(diameter_mm: float) -> float:
    return pi * diameter_mm**2 / 4.0


def design_concrete(
    project: ProjectModel,
    result: AnalysisResult,
    settings: ConcreteDesignSettings | None = None,
) -> ConcreteDesignResult:
    """
    Preliminary flexural reinforcement sizing.

    This is intentionally marked preliminary. It does not yet perform the full
    set of code checks required for production design, including ductility,
    shear, torsion interaction, development length, anchorage, seismic
    detailing, serviceability, crack width, column interaction or punching.
    """
    settings = settings or ConcreteDesignSettings()
    output = ConcreteDesignResult(settings)

    for frame in project.frames.values():
        if (
            frame.kind != "Beam"
            or frame.id not in result.frame_results
            or frame.section not in project.frame_sections
        ):
            continue
        section = project.frame_sections[frame.section]
        _, m2, _ = dominant_curve(result, frame.id, "Moment")
        governing = float(np.max(np.abs(m2)))
        effective_depth = (
            section.depth
            - settings.beam_cover_mm/1000.0
            - settings.beam_bar_diameter_mm/2000.0
        )
        required = _required_steel_area(
            governing, effective_depth,
            settings.steel_yield_mpa,
            settings.strength_reduction_factor,
        )
        minimum = (
            settings.minimum_reinforcement_ratio
            * section.width * section.depth * 1.0e6
        )
        required = max(required, minimum)
        count = max(
            2,
            int(np.ceil(
                required/_bar_area(settings.beam_bar_diameter_mm)
            )),
        )
        output.beams[frame.id] = BeamDesignResult(
            frame.id, governing, required, count,
            settings.beam_bar_diameter_mm,
            f"{count}Ø{settings.beam_bar_diameter_mm:g}",
        )

    for area in project.areas.values():
        if area.id not in result.area_results:
            continue
        area_result = result.area_results[area.id]
        mx = abs(float(area_result.resultants["Mx"]))
        my = abs(float(area_result.resultants["My"]))
        effective_depth = (
            area_result.thickness
            - settings.slab_cover_mm/1000.0
            - settings.slab_bar_diameter_mm/2000.0
        )
        as_x = _required_steel_area(
            mx, effective_depth,
            settings.steel_yield_mpa,
            settings.strength_reduction_factor,
        )
        as_y = _required_steel_area(
            my, effective_depth,
            settings.steel_yield_mpa,
            settings.strength_reduction_factor,
        )
        minimum = (
            settings.minimum_reinforcement_ratio
            * 1000.0 * area_result.thickness * 1000.0
        )
        as_x = max(as_x, minimum)
        as_y = max(as_y, minimum)
        bar_area = _bar_area(settings.slab_bar_diameter_mm)
        spacing_x = float(np.clip(
            bar_area*1000.0/as_x,
            settings.minimum_slab_spacing_mm,
            settings.maximum_slab_spacing_mm,
        ))
        spacing_y = float(np.clip(
            bar_area*1000.0/as_y,
            settings.minimum_slab_spacing_mm,
            settings.maximum_slab_spacing_mm,
        ))
        output.slabs[area.id] = SlabDesignResult(
            area.id, mx, my, as_x, as_y,
            spacing_x, spacing_y,
            settings.slab_bar_diameter_mm,
            f"Ø{settings.slab_bar_diameter_mm:g}@{spacing_x:.0f} X",
            f"Ø{settings.slab_bar_diameter_mm:g}@{spacing_y:.0f} Y",
        )

    output.warnings.extend([
        "Preliminary flexural sizing only.",
        "Independent engineering verification is required.",
        "Shear, punching, columns, seismic detailing and serviceability are not yet designed.",
    ])
    return output
