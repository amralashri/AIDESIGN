# FEM Verification Suite

This folder documents analytical benchmark models used by the automated tests.
All solver quantities use kN-m units.

Current benchmarks:

1. 3D cantilever tip force: `δ = PL³/(3EI)`.
2. Cantilever with an I-end rigid zone: deformable length is `L-oᵢ-oⱼ`.
3. 3D frame consistent mass: rigid-body translational mass equals `mL` in X/Y/Z.
4. Rigid-offset and consistent-mass matrices are symmetric and positive semidefinite within numerical tolerance.

These are analytical checks, not claims of complete commercial-software equivalence.
