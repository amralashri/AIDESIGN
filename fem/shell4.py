from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class ShellGeometry:
    rotation: np.ndarray
    local_xy: np.ndarray
    area: float


def shell_local_geometry(points: np.ndarray) -> ShellGeometry:
    """
    Create a local planar coordinate system for a four-node shell.

    Node order must follow the slab perimeter. The local z axis is the
    element normal; local x is node 1 -> node 2.
    """
    points = np.asarray(points, dtype=float)
    if points.shape != (4, 3):
        raise ValueError("Shell element requires four 3D corner points.")

    ex_vector = points[1] - points[0]
    ex_length = float(np.linalg.norm(ex_vector))
    if ex_length <= 1.0e-12:
        raise ValueError("Shell nodes 1 and 2 are coincident.")
    ex = ex_vector / ex_length

    normal = np.cross(points[1] - points[0], points[3] - points[0])
    normal_length = float(np.linalg.norm(normal))
    if normal_length <= 1.0e-12:
        raise ValueError("Shell element has zero or invalid area.")
    ez = normal / normal_length
    ey = np.cross(ez, ex)
    ey /= np.linalg.norm(ey)

    rotation = np.vstack((ex, ey, ez))
    origin = points[0]
    local = np.array([
        [
            float(np.dot(point-origin, ex)),
            float(np.dot(point-origin, ey)),
        ]
        for point in points
    ])

    # Shoelace area in local plane.
    x = local[:, 0]
    y = local[:, 1]
    area = 0.5 * abs(float(
        np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))
    ))
    if area <= 1.0e-12:
        raise ValueError("Shell element has zero area.")

    # Planarity check.
    distances = np.abs((points-origin) @ ez)
    if float(np.max(distances)) > 1.0e-6:
        raise ValueError("Shell corner nodes are not coplanar.")

    return ShellGeometry(rotation, local, area)


def shell_transformation(rotation: np.ndarray) -> np.ndarray:
    """24x24 local/global transformation, 6 DOF at each of 4 nodes."""
    transform = np.zeros((24, 24), dtype=float)
    for node in range(4):
        base = 6 * node
        transform[base:base+3, base:base+3] = rotation
        transform[base+3:base+6, base+3:base+6] = rotation
    return transform


def shape_functions(xi: float, eta: float):
    n = 0.25 * np.array([
        (1-xi)*(1-eta),
        (1+xi)*(1-eta),
        (1+xi)*(1+eta),
        (1-xi)*(1+eta),
    ], dtype=float)
    dxi = 0.25 * np.array([
        -(1-eta), +(1-eta), +(1+eta), -(1+eta)
    ], dtype=float)
    deta = 0.25 * np.array([
        -(1-xi), -(1+xi), +(1+xi), +(1-xi)
    ], dtype=float)
    return n, dxi, deta


def derivatives_xy(local_xy: np.ndarray, xi: float, eta: float):
    n, dxi, deta = shape_functions(xi, eta)
    jacobian = np.array([
        [np.dot(dxi, local_xy[:, 0]), np.dot(dxi, local_xy[:, 1])],
        [np.dot(deta, local_xy[:, 0]), np.dot(deta, local_xy[:, 1])],
    ], dtype=float)
    determinant = float(np.linalg.det(jacobian))
    if determinant <= 1.0e-12:
        raise ValueError(
            "Shell node order is reversed or element Jacobian is invalid."
        )
    gradients = np.linalg.inv(jacobian) @ np.vstack((dxi, deta))
    return n, gradients[0], gradients[1], determinant


def shell4_local_stiffness(
    elastic_modulus: float,
    poisson_ratio: float,
    thickness: float,
    local_xy: np.ndarray,
    shear_correction: float = 5.0/6.0,
) -> np.ndarray:
    """
    Four-node Mindlin-Reissner flat shell.

    Local nodal DOF:
      [u, v, w, rx, ry, rz] x 4

    Formulation:
      - bilinear Q4 membrane
      - Mindlin plate bending
      - reduced integration for transverse shear
      - small drilling-rotation stabilization
    """
    E = float(elastic_modulus)
    nu = float(poisson_ratio)
    t = float(thickness)
    if E <= 0.0 or t <= 0.0 or not (-0.49 < nu < 0.49):
        raise ValueError("Invalid shell material or thickness.")

    G = E / (2.0*(1.0+nu))
    membrane_d = E*t/(1.0-nu**2) * np.array([
        [1.0, nu, 0.0],
        [nu, 1.0, 0.0],
        [0.0, 0.0, (1.0-nu)/2.0],
    ])
    bending_d = E*t**3/(12.0*(1.0-nu**2)) * np.array([
        [1.0, nu, 0.0],
        [nu, 1.0, 0.0],
        [0.0, 0.0, (1.0-nu)/2.0],
    ])
    shear_d = shear_correction*G*t*np.eye(2)

    stiffness = np.zeros((24, 24), dtype=float)
    gauss = 1.0/np.sqrt(3.0)

    # Membrane and bending: 2x2 Gauss integration.
    for xi in (-gauss, gauss):
        for eta in (-gauss, gauss):
            _, dx, dy, det_j = derivatives_xy(local_xy, xi, eta)

            bm = np.zeros((3, 24), dtype=float)
            bb = np.zeros((3, 24), dtype=float)
            for node in range(4):
                base = 6*node
                # membrane [u,v]
                bm[0, base+0] = dx[node]
                bm[1, base+1] = dy[node]
                bm[2, base+0] = dy[node]
                bm[2, base+1] = dx[node]

                # curvatures from rotations rx, ry
                bb[0, base+4] = dx[node]       # kappa_x
                bb[1, base+3] = -dy[node]      # kappa_y
                bb[2, base+4] = dy[node]
                bb[2, base+3] = -dx[node]

            stiffness += (
                bm.T @ membrane_d @ bm
                + bb.T @ bending_d @ bb
            ) * det_j

    # Transverse shear: reduced one-point integration to limit locking.
    n, dx, dy, det_j = derivatives_xy(local_xy, 0.0, 0.0)
    bs = np.zeros((2, 24), dtype=float)
    for node in range(4):
        base = 6*node
        # gamma_xz = dw/dx + ry
        bs[0, base+2] = dx[node]
        bs[0, base+4] = n[node]
        # gamma_yz = dw/dy - rx
        bs[1, base+2] = dy[node]
        bs[1, base+3] = -n[node]
    stiffness += bs.T @ shear_d @ bs * det_j * 4.0

    # Drilling DOF stabilization, deliberately small.
    reference = max(float(np.max(np.diag(stiffness))), 1.0)
    drilling = reference * 1.0e-6
    for node in range(4):
        stiffness[6*node+5, 6*node+5] += drilling

    return (stiffness + stiffness.T) / 2.0


def shell_pressure_equivalent_local(
    normal_pressure: float,
    area: float,
) -> np.ndarray:
    """Consistent uniform normal pressure load for a Q4 shell."""
    load = np.zeros(24, dtype=float)
    nodal_force = float(normal_pressure) * float(area) / 4.0
    for node in range(4):
        load[6*node+2] = nodal_force
    return load


def shell_resultants_at(
    local_displacements: np.ndarray,
    elastic_modulus: float,
    poisson_ratio: float,
    thickness: float,
    local_xy: np.ndarray,
    xi: float,
    eta: float,
) -> dict[str, float]:
    """Membrane, moment and transverse-shear resultants at a natural point."""
    E = float(elastic_modulus)
    nu = float(poisson_ratio)
    t = float(thickness)
    G = E/(2.0*(1.0+nu))
    membrane_d = E*t/(1.0-nu**2) * np.array([
        [1.0,nu,0.0],[nu,1.0,0.0],[0.0,0.0,(1.0-nu)/2.0]
    ])
    bending_d = E*t**3/(12.0*(1.0-nu**2)) * np.array([
        [1.0,nu,0.0],[nu,1.0,0.0],[0.0,0.0,(1.0-nu)/2.0]
    ])
    shear_d = (5.0/6.0)*G*t*np.eye(2)

    n, dx, dy, _ = derivatives_xy(local_xy, xi, eta)
    bm = np.zeros((3,24))
    bb = np.zeros((3,24))
    bs = np.zeros((2,24))
    for node in range(4):
        base=6*node
        bm[0,base]=dx[node]
        bm[1,base+1]=dy[node]
        bm[2,base]=dy[node]
        bm[2,base+1]=dx[node]

        bb[0,base+4]=dx[node]
        bb[1,base+3]=-dy[node]
        bb[2,base+4]=dy[node]
        bb[2,base+3]=-dx[node]

        bs[0,base+2]=dx[node]
        bs[0,base+4]=n[node]
        bs[1,base+2]=dy[node]
        bs[1,base+3]=-n[node]

    membrane = membrane_d @ (bm @ local_displacements)
    moment = bending_d @ (bb @ local_displacements)
    shear = shear_d @ (bs @ local_displacements)
    return {
        "Nx": float(membrane[0]),
        "Ny": float(membrane[1]),
        "Nxy": float(membrane[2]),
        "Mx": float(moment[0]),
        "My": float(moment[1]),
        "Mxy": float(moment[2]),
        "Qx": float(shear[0]),
        "Qy": float(shear[1]),
    }


def shell_center_resultants(
    local_displacements: np.ndarray,
    elastic_modulus: float,
    poisson_ratio: float,
    thickness: float,
    local_xy: np.ndarray,
) -> dict[str, float]:
    return shell_resultants_at(
        local_displacements, elastic_modulus, poisson_ratio,
        thickness, local_xy, 0.0, 0.0,
    )


def shell_contour_samples(
    local_displacements: np.ndarray,
    elastic_modulus: float,
    poisson_ratio: float,
    thickness: float,
    local_xy: np.ndarray,
    divisions: int = 7,
) -> list[dict]:
    """Sample shell results over a regular natural-coordinate grid."""
    samples = []
    for eta in np.linspace(-1.0, 1.0, divisions):
        for xi in np.linspace(-1.0, 1.0, divisions):
            n, _, _, _ = derivatives_xy(local_xy, float(xi), float(eta))
            xy = n @ local_xy
            resultants = shell_resultants_at(
                local_displacements, elastic_modulus, poisson_ratio,
                thickness, local_xy, float(xi), float(eta),
            )
            w = float(sum(
                n[node] * local_displacements[6*node+2]
                for node in range(4)
            ))
            samples.append({
                "xi": float(xi), "eta": float(eta),
                "x": float(xy[0]), "y": float(xy[1]),
                "w": w, **resultants,
            })
    return samples


def natural_coordinates(
    local_xy: np.ndarray,
    point_xy: np.ndarray,
    tolerance: float = 1.0e-10,
    maximum_iterations: int = 25,
) -> tuple[float,float]:
    """Invert the Q4 isoparametric map using Newton iterations."""
    local_xy=np.asarray(local_xy,dtype=float)
    point_xy=np.asarray(point_xy,dtype=float)
    xi=0.0
    eta=0.0
    for _ in range(maximum_iterations):
        n,dxi,deta=shape_functions(xi,eta)
        current=n@local_xy
        residual=current-point_xy
        if float(np.linalg.norm(residual))<=tolerance:
            break
        jacobian=np.array([
            [np.dot(dxi,local_xy[:,0]),np.dot(deta,local_xy[:,0])],
            [np.dot(dxi,local_xy[:,1]),np.dot(deta,local_xy[:,1])],
        ],dtype=float)
        increment=np.linalg.solve(jacobian,residual)
        xi-=float(increment[0])
        eta-=float(increment[1])
    return float(xi),float(eta)


def shell_value_at_local_point(
    local_displacements: np.ndarray,
    elastic_modulus: float,
    poisson_ratio: float,
    thickness: float,
    local_xy: np.ndarray,
    point_xy: np.ndarray,
    key: str,
) -> float:
    xi,eta=natural_coordinates(local_xy,point_xy)
    xi=float(np.clip(xi,-1.0,1.0))
    eta=float(np.clip(eta,-1.0,1.0))
    if key=="w":
        n,_,_=shape_functions(xi,eta)
        return float(sum(
            n[node]*local_displacements[6*node+2]
            for node in range(4)
        ))
    return float(shell_resultants_at(
        local_displacements,elastic_modulus,poisson_ratio,
        thickness,local_xy,xi,eta,
    )[key])
