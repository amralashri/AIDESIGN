from __future__ import annotations

import numpy as np


def local_axes(point_i: np.ndarray, point_j: np.ndarray) -> np.ndarray:
    delta = point_j - point_i
    length = float(np.linalg.norm(delta))
    if length <= 1.0e-12:
        raise ValueError("Zero-length frame element.")

    ex = delta / length

    reference = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(ex, reference))) > 0.95:
        reference = np.array([0.0, 1.0, 0.0])

    ey = np.cross(reference, ex)
    ey /= np.linalg.norm(ey)
    ez = np.cross(ex, ey)

    # Rows transform a global vector into local components.
    return np.vstack((ex, ey, ez))


def transformation_matrix(rotation: np.ndarray) -> np.ndarray:
    transform = np.zeros((12, 12), dtype=float)
    for block in range(4):
        start = 3 * block
        transform[start:start+3, start:start+3] = rotation
    return transform


def local_stiffness_matrix(
    elastic_modulus: float,
    shear_modulus: float,
    area: float,
    iy: float,
    iz: float,
    torsion_constant: float,
    length: float,
) -> np.ndarray:
    if min(
        elastic_modulus, shear_modulus, area, iy, iz,
        torsion_constant, length,
    ) <= 0.0:
        raise ValueError("Frame stiffness properties must be positive.")

    E = elastic_modulus
    G = shear_modulus
    A = area
    L = length
    J = torsion_constant

    matrix = np.zeros((12, 12), dtype=float)

    # Axial
    axial = E * A / L
    matrix[0,0] = matrix[6,6] = axial
    matrix[0,6] = matrix[6,0] = -axial

    # Saint-Venant torsion
    torsion = G * J / L
    matrix[3,3] = matrix[9,9] = torsion
    matrix[3,9] = matrix[9,3] = -torsion

    # Bending about local z: local-y translation / local-z rotation.
    c1 = 12.0 * E * iz / L**3
    c2 = 6.0 * E * iz / L**2
    c3 = 4.0 * E * iz / L
    c4 = 2.0 * E * iz / L
    dof = [1, 5, 7, 11]
    block = np.array([
        [ c1,  c2, -c1,  c2],
        [ c2,  c3, -c2,  c4],
        [-c1, -c2,  c1, -c2],
        [ c2,  c4, -c2,  c3],
    ])
    matrix[np.ix_(dof, dof)] += block

    # Bending about local y: local-z translation / local-y rotation.
    c1 = 12.0 * E * iy / L**3
    c2 = 6.0 * E * iy / L**2
    c3 = 4.0 * E * iy / L
    c4 = 2.0 * E * iy / L
    dof = [2, 4, 8, 10]
    block = np.array([
        [ c1, -c2, -c1, -c2],
        [-c2,  c3,  c2,  c4],
        [-c1,  c2,  c1,  c2],
        [-c2,  c4,  c2,  c3],
    ])
    matrix[np.ix_(dof, dof)] += block

    return matrix


def uniform_load_equivalent_local(
    qx: float,
    qy: float,
    qz: float,
    length: float,
) -> np.ndarray:
    """
    Consistent nodal load vector for a constant local member load.
    Positive q components act along positive local axes.
    """
    L = length
    load = np.zeros(12, dtype=float)

    load[0] += qx * L / 2.0
    load[6] += qx * L / 2.0

    load[1] += qy * L / 2.0
    load[5] += qy * L**2 / 12.0
    load[7] += qy * L / 2.0
    load[11] -= qy * L**2 / 12.0

    load[2] += qz * L / 2.0
    load[4] -= qz * L**2 / 12.0
    load[8] += qz * L / 2.0
    load[10] += qz * L**2 / 12.0

    return load


def apply_end_releases(
    local_stiffness: np.ndarray,
    local_load: np.ndarray,
    release_i: tuple[bool,bool,bool,bool,bool,bool],
    release_j: tuple[bool,bool,bool,bool,bool,bool],
) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """
    Apply member-end releases by static condensation.

    Returns:
      condensed 12x12 stiffness,
      condensed equivalent load vector,
      released local DOF indices.

    Translational releases are supported mathematically but may create a
    mechanism. Typical beam hinges release local rotations only.
    """
    released = np.array(
        [index for index,flag in enumerate((*release_i,*release_j)) if flag],
        dtype=int,
    )
    if released.size == 0:
        return local_stiffness.copy(), local_load.copy(), released

    retained = np.setdiff1d(np.arange(12,dtype=int), released)
    if retained.size == 0:
        raise ValueError("All frame end DOFs cannot be released.")

    krr = local_stiffness[np.ix_(retained,retained)]
    krs = local_stiffness[np.ix_(retained,released)]
    ksr = local_stiffness[np.ix_(released,retained)]
    kss = local_stiffness[np.ix_(released,released)]

    # Pseudo-inverse handles independent released modes safely.
    inverse = np.linalg.pinv(kss, rcond=1.0e-12)
    condensed_rr = krr - krs @ inverse @ ksr
    condensed_load_r = (
        local_load[retained]
        - krs @ inverse @ local_load[released]
    )

    condensed = np.zeros((12,12),dtype=float)
    load = np.zeros(12,dtype=float)
    condensed[np.ix_(retained,retained)] = condensed_rr
    load[retained] = condensed_load_r

    # Tiny stabilization only on released rows avoids exact numerical noise
    # without transferring meaningful end force.
    reference = max(float(np.max(np.abs(np.diag(local_stiffness)))),1.0)
    for dof in released:
        condensed[dof,dof] = reference*1.0e-12

    return (condensed+condensed.T)/2.0, load, released


def local_geometric_stiffness(
    axial_force_compression: float,
    length: float,
) -> np.ndarray:
    """
    Initial-stress geometric stiffness for a 3D frame.

    Positive axial_force_compression means compression. The same classical
    beam-column matrix is assembled in both local bending planes.
    """
    p = float(axial_force_compression)
    L = float(length)
    matrix = np.zeros((12,12),dtype=float)
    if abs(p) <= 1.0e-15:
        return matrix

    coefficient = p/(30.0*L)
    block = coefficient*np.array([
        [ 36.0,  3.0*L, -36.0,  3.0*L],
        [  3.0*L, 4.0*L*L, -3.0*L, -1.0*L*L],
        [-36.0, -3.0*L,  36.0, -3.0*L],
        [  3.0*L, -1.0*L*L, -3.0*L, 4.0*L*L],
    ],dtype=float)

    # local-y translation / local-z rotation
    dof_y = [1,5,7,11]
    matrix[np.ix_(dof_y,dof_y)] += block

    # local-z translation / local-y rotation; signs follow local convention.
    dof_z = [2,4,8,10]
    sign = np.diag([1.0,-1.0,1.0,-1.0])
    matrix[np.ix_(dof_z,dof_z)] += sign @ block @ sign

    return (matrix+matrix.T)/2.0


def rigid_end_offset_matrix(offset_i: float, offset_j: float) -> np.ndarray:
    """Map local joint DOFs to deformable member-face DOFs.

    Offsets are positive distances measured from each joint toward the member
    interior along local x. The transformation includes rigid-arm coupling
    between joint rotations and face translations.
    """
    oi=float(offset_i); oj=float(offset_j)
    if oi < 0.0 or oj < 0.0:
        raise ValueError("Rigid end offsets cannot be negative.")
    transform=np.eye(12,dtype=float)
    # u_face = u_joint + theta x r.  r_i=(+oi,0,0), r_j=(-oj,0,0)
    # theta x r = [0, rz*r_x, -ry*r_x]
    transform[1,5] += oi
    transform[2,4] -= oi
    transform[7,11] -= oj
    transform[8,10] += oj
    return transform


def apply_rigid_end_offsets(
    local_stiffness: np.ndarray,
    local_load: np.ndarray,
    offset_i: float,
    offset_j: float,
) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """Transform face stiffness/load to joint-centre DOFs."""
    arm=rigid_end_offset_matrix(offset_i,offset_j)
    return arm.T@local_stiffness@arm, arm.T@local_load, arm


def local_consistent_mass_matrix(
    mass_per_length: float,
    rotary_mass_per_length: float,
    length: float,
) -> np.ndarray:
    """Consistent 12x12 Euler-Bernoulli frame mass matrix.

    ``mass_per_length`` is translational mass per unit length. The matrix
    includes axial and both flexural planes. ``rotary_mass_per_length`` is
    the polar rotary inertia per unit length used for Saint-Venant rotation.
    """
    m=float(mass_per_length); r=float(rotary_mass_per_length); L=float(length)
    if m < 0.0 or r < 0.0 or L <= 0.0:
        raise ValueError("Mass properties must be non-negative and length positive.")
    matrix=np.zeros((12,12),dtype=float)
    # axial
    axial=m*L/6.0*np.array([[2.0,1.0],[1.0,2.0]])
    matrix[np.ix_([0,6],[0,6])] += axial
    # torsional rotary inertia
    torsion=r*L/6.0*np.array([[2.0,1.0],[1.0,2.0]])
    matrix[np.ix_([3,9],[3,9])] += torsion
    # bending consistent mass, transverse y / rotation z
    block=m*L/420.0*np.array([
        [156.0, 22.0*L, 54.0, -13.0*L],
        [22.0*L, 4.0*L*L, 13.0*L, -3.0*L*L],
        [54.0, 13.0*L, 156.0, -22.0*L],
        [-13.0*L, -3.0*L*L, -22.0*L, 4.0*L*L],
    ])
    matrix[np.ix_([1,5,7,11],[1,5,7,11])] += block
    # transverse z / rotation y uses opposite rotation convention
    sign=np.diag([1.0,-1.0,1.0,-1.0])
    matrix[np.ix_([2,4,8,10],[2,4,8,10])] += sign@block@sign
    return (matrix+matrix.T)/2.0
