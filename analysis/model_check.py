from __future__ import annotations

from dataclasses import dataclass, field

from model.project import ProjectModel
from analysis.shell_quality import evaluate_shell_quality
import numpy as np


@dataclass(slots=True)
class ModelCheckReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def as_text(self) -> str:
        lines = [
            "AIDESIGN MODEL CHECK",
            "=" * 48,
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
        ]
        if self.errors:
            lines += ["", "ERRORS:"]
            lines += [f"- {item}" for item in self.errors]
        if self.warnings:
            lines += ["", "WARNINGS:"]
            lines += [f"- {item}" for item in self.warnings]
        if not self.errors and not self.warnings:
            lines += ["", "No model problems were detected."]
        return "\n".join(lines)


def check_model(project: ProjectModel) -> ModelCheckReport:
    report = ModelCheckReport()

    if not project.nodes:
        report.errors.append("The model contains no joints.")
    if not project.frames and not project.areas:
        report.errors.append(
            "The model contains no frame or shell elements."
        )

    if project.nodes and not any(any(node.restraint) for node in project.nodes.values()):
        report.errors.append("No joint restraints are assigned.")

    connectivity = {node_id: 0 for node_id in project.nodes}
    for diaphragm in project.diaphragms.values():
        if len(diaphragm.node_ids)<2:
            report.errors.append(
                f"Diaphragm {diaphragm.name} has fewer than two joints."
            )
        elevations={
            round(project.nodes[nid].z,8)
            for nid in diaphragm.node_ids
            if nid in project.nodes
        }
        if len(elevations)>1:
            report.errors.append(
                f"Diaphragm {diaphragm.name} contains joints at "
                f"different elevations."
            )

    for frame in project.frames.values():
        if frame.i not in project.nodes or frame.j not in project.nodes:
            report.errors.append(
                f"Frame F{frame.id} references a missing joint."
            )
            continue
        ni = project.nodes[frame.i]
        nj = project.nodes[frame.j]
        length_sq = (
            (ni.x-nj.x)**2 + (ni.y-nj.y)**2 + (ni.z-nj.z)**2
        )
        if length_sq <= 1.0e-16:
            report.errors.append(f"Frame F{frame.id} has zero length.")
        else:
            length=length_sq**0.5
            if frame.rigid_offset_i < 0.0 or frame.rigid_offset_j < 0.0:
                report.errors.append(
                    f"Frame F{frame.id} has a negative rigid end offset."
                )
            if frame.rigid_offset_i+frame.rigid_offset_j >= length-1.0e-8:
                report.errors.append(
                    f"Frame F{frame.id} rigid offsets consume the member length."
                )
        if all(frame.release_i[3:]) and all(frame.release_j[3:]):
            report.warnings.append(
                f"Frame F{frame.id} releases all rotations at both ends; "
                "check for a mechanism."
            )
        connectivity[frame.i] += 1
        connectivity[frame.j] += 1
        if frame.section not in project.frame_sections:
            report.errors.append(
                f"Frame F{frame.id} uses undefined section '{frame.section}'."
            )
        for pattern in frame.distributed_loads:
            if pattern not in project.load_patterns:
                report.errors.append(
                    f"Frame F{frame.id} uses undefined load pattern '{pattern}'."
                )

    area_nodes = set()
    for area in project.areas.values():
        area_nodes.update(area.nodes)
        if area.section not in project.area_sections:
            report.errors.append(
                f"Area A{area.id} uses undefined section '{area.section}'."
            )
        if len(set(area.nodes)) != 4:
            report.errors.append(
                f"Area A{area.id} must contain four unique joints."
            )
        for pattern in area.surface_loads:
            if pattern not in project.load_patterns:
                report.errors.append(
                    f"Area A{area.id} uses undefined load pattern "
                    f"'{pattern}'."
                )
        try:
            points=np.array([
                [project.nodes[nid].x,project.nodes[nid].y,project.nodes[nid].z]
                for nid in area.nodes
            ],dtype=float)
            quality=evaluate_shell_quality(points,area.id)
            if quality.status=="Poor":
                report.errors.append(
                    f"Area A{area.id} has poor mesh quality "
                    f"(aspect={quality.aspect_ratio:.2f}, "
                    f"min angle={quality.minimum_angle_deg:.1f}°, "
                    f"Jacobian={quality.jacobian_ratio:.3f})."
                )
            elif quality.status=="Warning":
                report.warnings.append(
                    f"Area A{area.id} has marginal mesh quality "
                    f"(score={quality.quality_score:.2f})."
                )
        except Exception as exc:
            report.errors.append(
                f"Area A{area.id} geometry is invalid: {exc}"
            )

    for node_id, count in connectivity.items():
        if count == 0 and node_id not in area_nodes:
            report.warnings.append(f"Joint N{node_id} is unconnected.")

    for load in project.joint_loads:
        if load.node_id not in project.nodes:
            report.errors.append(
                f"A joint load references missing joint N{load.node_id}."
            )
        if load.pattern not in project.load_patterns:
            report.errors.append(
                f"A joint load uses undefined pattern '{load.pattern}'."
            )

    return report
