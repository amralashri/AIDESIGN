# AIDESIGN v1.5.0 — FEM Core Sprint 1

## Frame3D core upgrades

- Added rigid I-end and J-end offsets measured from the analytical joint toward the member interior.
- Rigid-arm transformations now couple joint rotations to member-face translations.
- Frame stiffness and consistent member loads are transformed from member faces to joint-centre DOFs.
- Internal forces are recovered at the deformable member faces, not from the rigid-zone joint matrix.
- End releases remain applied by static condensation before rigid-zone transformation.

## Consistent frame mass

The modal solver now uses a full 12×12 Euler-Bernoulli consistent mass matrix for frame self-mass, including:

- axial translational mass;
- two flexural consistent-mass planes;
- torsional rotary inertia;
- rigid-end-offset transformation;
- global-coordinate transformation.

Load-derived and shell masses remain lumped in this sprint.

## Stability diagnostics

Singular or non-finite solutions now report:

- zero-stiffness joint DOFs;
- dominant DOFs in the softest stiffness mode;
- an estimated stiffness condition number where it can be evaluated.

Model Check also validates rigid-offset length and warns about frames releasing all rotations at both ends.

## Interface

A new command is available for selected frames:

`Assign → Assign Rigid End Offsets...`

The Assign ribbon also includes a **Rigid Offsets** button. Values are saved in `.aidesign` project files and old files load with zero offsets.

## Verification

Automated analytical checks include:

- cantilever tip displacement `PL³/(3EI)`;
- cantilever with a shortened deformable length caused by a rigid end zone;
- rigid-arm kinematic mapping;
- consistent-mass rigid-body translational mass;
- symmetry and positive-semidefinite mass checks;
- project serialization compatibility.

This sprint strengthens the current Euler-Bernoulli frame core. It does not yet claim MITC4 shell replacement, Timoshenko shear deformation, warping torsion, nonlinear material behavior, or commercial-program certification.

# AIDESIGN v1.4 — Frame Releases, Rigid Diaphragms and P-Delta

## Frame end releases

Select frame objects and use:

- Assign > Assign Frame End Releases
- or the Releases button in the Assign ribbon group

Supported local end releases:

- U1, U2, U3
- R1, R2, R3
- independent I-end and J-end releases
- Pin I, Pin J and Pin Both presets

The solver applies releases by static condensation of the local
12-DOF frame stiffness and consistent member-load vector. Released end
forces are reported as zero.

## Rigid diaphragms

Select floor slabs or horizontal frame objects and assign a diaphragm.

The diaphragm can tie:

- global Ux
- global Uy
- global Rz

All assigned joints must be at one elevation. The current implementation
uses a high-stiffness penalty constraint and is suitable for linear and
P-Delta analysis development.

## P-Delta analysis

Analyze > Run P-Delta Analysis performs iterative second-order analysis.

Workflow:

1. solve the first-order model;
2. recover compressive axial forces;
3. assemble frame geometric stiffness;
4. solve the updated tangent system;
5. repeat until relative displacement convergence.

The user controls:

- maximum iterations
- convergence tolerance

The Results panel displays the converged displacements and frame forces.
The Output panel reports iteration count and final relative error.

## Engineering limitations

This is an initial-stress P-Delta implementation. It is not yet a full
large-displacement nonlinear solver.

Not included yet:

- P-small-delta member curvature effects beyond the geometric matrix
- nonlinear material behavior
- tension-only or compression-only objects
- staged construction
- automatic load-case sequencing
- exact multipoint-constraint transformation for diaphragms
- buckling eigenvalue analysis


# AIDESIGN v1.3 — Window Selection, 3D Animation and Codes

## Professional drag selection in Plan View

Select mode now supports press-drag-release selection.

- Drag left to right: Window selection
  - selects frames and slabs fully contained inside the rectangle
  - shown with a blue selection window
- Drag right to left: Crossing selection
  - selects objects inside or intersected by the rectangle
  - shown with a green crossing window
- A short click continues to select a single object.
- Ctrl preserves the current selection and adds window-selected objects.
- Escape cancels an active selection window.

## Smaller professional left toolbar

The left toolbar now uses 31 x 31 pixel buttons with larger colored
symbols, hover highlighting and command tooltips.

Additional shortcuts include:

- New, Open and Save
- Select / Window Select
- Beam, Column and Slab
- Shell Mesh
- Delete
- Grids and Frame Sections
- Frame and Slab Loads
- Codes and Standards
- Fit Plan and Isometric 3D
- Check Model and Run Analysis
- Animate Deformed Shape
- Animate Mode Shape
- Stop Animation

## 3D deformed-shape animation

Display > Start Deformed Shape Animation animates the static deformed
shape from the undeformed position to the fully amplified shape and
back.

Display > Start Mode Shape Animation animates the selected eigenmode
between its positive and negative amplitudes.

Animation controls include:

- start static deformation
- start selected mode
- stop
- speed from 0.25x to 2.00x

The animation is a visualization of calculated displacement or
eigenvector results. It is not a nonlinear time-history simulation.

## Codes and Standards tab

A dedicated Codes ribbon tab and a persistent Codes & Standards dock
have been added.

Saved project settings include:

- concrete design code
- loading code
- steel code
- seismic code
- wind code
- importance factor
- concrete flexural phi factor
- concrete shear phi factor
- LRFD / ASD steel method
- project code notes

The selected flexural and shear phi factors are now passed into the
preliminary concrete design engine.

These selections document and configure the project. They do not imply
that every clause of the selected standard has already been implemented.
Each analysis and design module must still be independently validated.


# AIDESIGN v1.2 — Compact Left Tools, Exact Slab Data Tips, Mesh and DXF

## Compact vertical tool column

The large working controls have been reduced and a permanent compact
toolbar has been added on the left side.

It contains clear symbol buttons for:

- selection
- beam drawing
- column drawing
- slab drawing
- slab finite-element division
- delete
- fit full plan grid
- isometric 3D
- model check
- run analysis

Only the symbols remain visible. Hovering over any symbol displays its
full command name and status description.

The upper ribbon has also been reduced in height and button size.

## Exact slab values under the mouse

Slab data tips no longer use the nearest fixed contour sample.

The pointer position is transformed into the shell local coordinate
system, the Q4 natural coordinates are solved iteratively, and the
selected result is evaluated at the actual pointer location.

This applies to:

- Mx
- My
- Mxy
- Qx
- Qy
- slab deflection

The 3D viewport now intersects the camera ray with the slab plane and
uses the exact hit position rather than a nearby rendered sample.

## Divide slab / finite-element mesh

Select one or more slabs and use:

- Draw > Divide / Mesh Selected Slab
- or the mesh symbol in the left toolbar

Specify the local X and Y division counts. The original slab is replaced
by conforming Q4 shell elements.

The mesh operation preserves:

- slab section
- slab material through the section
- surface-load assignments
- shared internal nodes

## Full-grid Plan default

Plan View now performs Fit Grid after it becomes visible, after project
replacement and after story changes. The default view displays all grid
lines and labels with margins.

## DXF import

File > Import DXF imports:

- LINE entities as beam objects
- open polylines as connected beam segments
- closed four-vertex polylines as slab objects

The import dialog supports source coordinates in m, mm, cm, ft or in.

DXF support uses the `ezdxf` package and is installed automatically by
`run.bat` through the updated requirements file.


# AIDESIGN v1.1 — Modal Analysis and Mode Shapes

## Mass source

The structural model now contains a configurable mass source:

- element self-mass
- load-pattern mass factors
- explicit six-component joint masses

Default load-derived mass factors:

- DEAD = 1.00
- LIVE = 0.25

## Modal analysis

A new undamped eigenvalue solver calculates:

- eigenvalues
- circular frequencies
- frequencies in Hz
- periods in seconds
- mode-shape vectors
- directional participation indicators

Frame and shell stiffness are assembled in the same dynamic model.

## Integrated modal results

A permanent Modal Analysis dock displays all calculated modes.

Mode shapes appear directly in:

- Plan View
- 3D View

The active mode may be changed from the dock without opening a modal
results window.

## Current dynamic-analysis scope

- linear elastic eigenvalue analysis
- lumped translational element mass
- explicit joint translational and rotational mass
- fixed support restraints
- frame and shell stiffness

Not included yet:

- response spectrum
- time history
- damping models
- diaphragm constraints
- accidental torsion
- Ritz vectors
- nonlinear modal analysis


# AIDESIGN v1.0 — Interactive Data Tips and Display Units

## Result values under the mouse pointer

Move the pointer over a displayed result to inspect its value at the
nearest station or sampled shell point.

Plan View supports moment, shear, axial force, torsion, slab contours,
support reactions and deformed-joint displacements.

3D View supports frame-force diagrams and colored slab contours.

The data tip reports the object, component, location, converted value,
unit and active analysis case.

## Unit controls at the lower-right status bar

Independent display selectors are available for:

- length
- area
- force
- moment
- stress
- displacement

The selections update cursor coordinates, analysis tables, maximum
displacement and interactive result data tips immediately.

The structural solver continues to use consistent internal kN-m units.
Changing a display unit never modifies the stiffness matrix, model
coordinates, loads or saved structural data.


# AIDESIGN v0.8 — Slab Contours and Preliminary RC Design

## Colored slab contours

The program now displays colored slab contours in both Plan and 3D:

- Mx
- My
- Mxy
- Qx
- Qy
- Vertical slab deflection in mm

Features include:

- blue-to-red engineering color scale
- shared model-wide minimum and maximum
- color legend
- sampled shell values across every Q4 slab
- contour cell shading
- result selection from Display and the Results panel

## Preliminary concrete design

A preliminary reinforced-concrete flexural sizing engine has been added.

Beam output:

- governing bending moment
- required longitudinal steel area
- preliminary number and diameter of bars
- reinforcement label shown on Plan and 3D

Slab output:

- Mx and My design strips at the shell centre
- required reinforcement per metre in X and Y
- preliminary bar spacing
- reinforcement lines and labels displayed on Plan and 3D

## Important engineering limitation

The concrete design in this release is preliminary flexural sizing only.
It is not a complete code-certified design.

It does not yet include:

- beam and slab shear design
- punching shear
- column P-M interaction
- torsion interaction
- development and anchorage
- seismic detailing
- crack width and long-term deflection
- load envelopes and design combinations by code
- detailing around supports and openings

Independent verification by a qualified structural engineer is mandatory.

## Remaining development stages

The next planned modules are:

- shell meshing and result smoothing
- frame end releases and rigid offsets
- P-Delta analysis
- modal analysis
- response-spectrum analysis
- punching shear
- complete beam, column and slab code design
- reinforcement detailing and reports


# AIDESIGN v0.7 — Shell FEM, Isometric Startup, Modern Home Ribbon

## Default 3D view

- The 3D viewport now opens in a true Isometric view.
- Opening or creating another project restores Isometric automatically.
- The pivot remains at the grid centre.
- The Home button labelled `Isometric` restores the same default view.

## Slab definition

A new `Define > Slab Sections` dialog supports:

- Slab section name
- Material
- Thickness
- Shell formulation label

The default section is S200 with 200 mm thickness.

## Slab loading

A new `Assign > Assign Slab Load` command assigns downward surface
loads in kN/m² to one or more selected slab areas.

Slab self-weight is calculated from:

- material density
- slab thickness
- load-pattern self-weight multiplier

## Real slab / shell FEM analysis

Slabs are no longer graphics-only objects. This release assembles a
four-node Mindlin-Reissner flat-shell element into the same global
stiffness matrix used by frames.

Each shell corner uses six global DOF. The formulation includes:

- in-plane membrane stiffness
- plate bending stiffness
- transverse shear stiffness
- reduced shear integration
- drilling-rotation stabilization
- local/global transformation
- consistent uniform pressure loading
- slab self-weight
- centre membrane forces Nx, Ny, Nxy
- centre bending moments Mx, My, Mxy
- centre shear resultants Qx, Qy

Shell resultants appear in a new permanent Results tab.

## Modern Home / Ribbon redesign

The second row has been rebuilt with:

- modern tab styling
- rounded group cards
- consistent spacing and button sizes
- clearer symbols
- grouped Project, Modify, Create Model, Analysis and View tools
- a more compact and organized Home tab
- dedicated Define and Assign tools for slab sections and slab loads

## Engineering scope and limits

The shell implementation is a linear, flat, four-node Mindlin element.
It is suitable for development and benchmark comparison, but it is not
yet claimed as a certified replacement for commercial software.

Not yet included:

- shell mesh subdivision
- geometric nonlinearity / P-Delta
- frame end releases
- rigid end offsets
- modal and response-spectrum analysis
- concrete reinforcement design


# AIDESIGN v0.6 — Grid-Centre Pivot and Inline Results

## 3D pivot correction

- The default orbit pivot is now the exact geometric centre of the grid extents.
- X pivot = (minimum X grid + maximum X grid) / 2.
- Y pivot = (minimum Y grid + maximum Y grid) / 2.
- Z pivot = midpoint between the lowest and highest story elevations.
- Reset, Fit, Isometric, Top, Front, and Right views preserve this grid-centre pivot.
- Double-clicking a frame still permits a temporary Revit-style local pivot.
- Double-clicking empty space returns the pivot to the grid centre.

## Results no longer open in a pop-up

After analysis, results are displayed inside a permanent docked panel:

- Joint displacements
- Support reactions
- Frame local end forces
- Analysis case and maximum displacement summary
- Result display selector

## Results displayed in both Plan and 3D

Available displays:

- Undeformed model
- Deformed shape
- Moment diagrams
- Shear diagrams
- Axial-force diagrams
- Torsion diagrams
- Support reactions

The selected result mode updates Plan View and 3D View together.

## Continued project stage

- Embedded result browser
- Persistent result tabs
- Automatic deformed-shape display after analysis
- Result values annotated directly on the model
- Support reactions drawn on the plan
- No modal pop-up interrupts model navigation

## Current engineering scope

- Linear elastic, first-order 3D frame analysis
- 6 DOF per joint
- Axial, biaxial bending and torsion
- Uniform member loads, joint loads and self-weight
- Load patterns and combinations

Shell stiffness, P-Delta, frame releases, rigid zones and concrete design
remain subsequent stages and are not claimed in this release.


# AIDESIGN v0.5 — Revit-Style Camera and Load Management

## Corrected 3D default view

- Perspective projection instead of the previous orthographic fixed-point view.
- Correct south-east isometric startup with global Z visibly upward.
- The default model is no longer upside down.
- Fit View centres the actual model bounding box.
- The camera does not remain attached to the world origin.

## Revit-style 3D navigation

- Left-drag: orbit around the current pivot.
- Middle-drag: pan the camera and pivot together.
- Mouse wheel: smooth dolly zoom.
- Double-click a frame: move the orbit pivot to the clicked location.
- Double-click empty space: restore pivot to model centre.
- Right-click a frame: select it in 3D.
- Isometric, Top, Front, Right, Fit, and Reset commands retained.
- Global Z stays upright and the view cannot unexpectedly flip upside down.
- Perspective axis triad remains fixed on screen.

## Next project stage included

- Define Load Patterns.
- Edit self-weight multiplier for every load pattern.
- Define and edit Load Combinations.
- Generate standard ULS/SLS combinations.
- Validate combination factors against existing patterns.
- Preserve patterns and combinations in `.aidesign` project files.
- New Ribbon buttons and Define-menu commands.

## Verification

The release includes camera-orientation, pivot, perspective-projection,
load-combination, FEM, and postprocessing tests.


# AIDESIGN v0.4 — Stability, Free 3D Orbit, and Postprocessing

## Interface corrections

- All principal menus now contain connected actions.
- Working Define dialogs:
  - Grid systems
  - Story data
  - Materials
  - Frame sections
- Working Select menu:
  - Select all visible
  - Clear selection
- Working View menu:
  - Fit Plan
  - Fit 3D
  - Isometric
  - Top
  - Front
  - Right
  - Reset dock layout
- Working Assign, Analyze, Display, Tools, and Help actions.

## Fully free 3D viewport

- Unrestricted matrix-based orbit without elevation clamps.
- Left mouse: orbit in every direction.
- Middle mouse: pan.
- Right mouse: camera roll.
- Wheel: zoom.
- Double-click: fit model.
- Fit, Isometric, Top, Front, and Right view commands.
- Fixed screen-overlay axis triad and instructions.
- Base grid remains at the lowest story.

## Next-stage postprocessing added

- Deformed shape with automatic display scale.
- 3D moment diagrams.
- 3D shear diagrams.
- 3D axial-force diagrams.
- Continuous internal-force recovery at member stations.
- Global diagram normalization.
- Maximum values annotated on the model.

## Important limits

- Results remain linear first-order frame analysis.
- Area/shell stiffness is not assembled yet.
- No P-Delta or end releases in this release.


# AIDESIGN v0.3 — FEM Core

## Added in this release

- 3D Euler-Bernoulli space-frame element.
- 6 DOF per joint and 12 DOF per frame.
- Axial, biaxial bending, and torsional stiffness.
- Local-to-global transformation matrix.
- Sparse global stiffness assembly using SciPy.
- Joint restraints and fixed-base assignment.
- Joint loads.
- Global uniform frame loads.
- Automatic frame self-weight.
- Load patterns and ULS/SLS combinations.
- Joint displacements, support reactions, and local frame end forces.
- Model Check before analysis.
- Results window in the GUI.
- Numerical verification tests:
  - stiffness symmetry;
  - transformation orthogonality;
  - cantilever closed-form tip deflection;
  - cantilever support reaction.

## Use

1. Run `run.bat`.
2. Draw the frame model.
3. Select `Assign > Assign Fixed Base`.
4. Select beams and use `Assign > Assign Frame UDL`.
5. Select an analysis case from the top toolbar.
6. Use `Analyze > Check Model`.
7. Use `Analyze > Run Analysis`.

## Run verification tests

Double-click:

```text
run_tests.bat
```

## Current analysis limits

- Linear elastic, first-order static analysis.
- Euler-Bernoulli frame theory.
- No frame end releases yet.
- No rigid end zones yet.
- No P-Delta yet.
- Slabs are stored and drawn but are not included in stiffness assembly.


# AIDESIGN v0.2 Bootstrap

## Fastest Windows startup

1. Extract the ZIP to a normal folder.
2. Double-click `run.bat`.
3. On the first run, required Python packages are installed automatically.
4. The program starts after installation.

## Manual installation

```powershell
py -m pip install -r requirements.txt
py main.py
```

## Diagnostic tools

- `install.bat`: installs all required packages.
- `check_environment.bat`: checks Python, PySide6, NumPy, and SciPy.
- `run.bat`: installs missing packages automatically and launches AIDESIGN.

## Important

Do not run `main.py` before installing the requirements unless you use `run.bat`.


# AIDESIGN v0.1 — Sprint 1

Private structural modeling desktop application foundation.

## Implemented

- PySide6 professional desktop interface.
- ETABS-style menu and tabbed ribbon.
- Dockable Model Explorer, Object Properties and Output panes.
- Persistent Plan and isometric 3D viewports.
- Story and grid system database.
- Beam drawing by click-drag-release.
- Live rubber-band preview while dragging.
- Grid, endpoint and midpoint snapping.
- Orthogonal drawing with Shift.
- Beam, column and rectangular slab tools.
- Hover highlight and plan selection.
- Multi-selection with Ctrl.
- Middle-button pan and cursor-centered wheel zoom.
- Project save/open using `.aidesign` JSON files.
- Light professional theme.

## Run

```powershell
py -m pip install -r requirements.txt
py main.py
```

## Scope note

This sprint establishes the CAD/UI/model database foundation. It does not yet perform structural analysis. FEM will be developed and validated in the next sprint.
