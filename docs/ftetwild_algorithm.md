# fTetWild Algorithm Overview

Based on the paper "Fast Tetrahedral Meshing in the Wild" (arXiv:1908.03581) and source code analysis.

## Core Idea

fTetWild takes a triangle surface mesh (possibly with defects, self-intersections) and generates a high-quality tetrahedral volume mesh. It uses the **envelope** concept to guarantee the output surface stays within epsilon distance of the input surface.

## Two Key Parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `ideal_edge_length` (`-l`) | bbox_diag / 20 | Target edge length, controls mesh density |
| `epsilon` (`-e`) | bbox_diag / 1000 | Envelope thickness, controls surface approximation accuracy |

## 8-Step Pipeline

### Step 1: Simplification

Preprocess the input surface mesh:
- Merge duplicate vertices within epsilon distance
- Collapse very short edges
- Swap edges to improve quality

Purpose: simplify input to reduce downstream computation.

### Step 2: Delaunay Triangulation

Generate initial tet mesh inside the bounding box:
- Expand bbox by `max(ideal_edge_length, 2*eps)`
- Place grid points inside bbox at `bbox_diag/15` spacing
- Add input surface vertices
- Call Geogram's 3D Delaunay

Result: a coarse ~4000-vertex tet mesh.

### Step 3: Triangle Insertion

Cut input surface triangles into the tet mesh:
- Find which tets each input triangle intersects
- Cut tets so their faces align with input triangles
- Track which input faces have been successfully inserted

This is the core difference from TetWild: TetWild uses exact rational arithmetic, fTetWild uses floating-point and interleaves insertion with optimization.

### Step 4: Optimization Loop (up to 80 passes)

Each pass executes 4 operations in sequence:

**Edge Splitting:**
- Condition: edge length > `ideal_edge_length * 4/3`
- Operation: insert new vertex at midpoint, split edge in two
- Priority: longest edges first

**Edge Collapsing:**
- Condition: edge length < `ideal_edge_length * 4/5`
- Constraints:
  - New tets must not invert (inversion check)
  - Quality must not degrade
  - Vertices must stay within envelope
- Priority: shortest edges first
- Iterative: collapse → creates new short edges → collapse again → until no more collapsible edges (do-while loop)

**Edge Swapping:**
- Condition: interior edges with 3/4/5 adjacent tets
- Operations: reorganize topology (3→2, 4→4, 5→6 tet configurations)
- Constraint: all new tets must have strictly better quality than the old ones

**Vertex Smoothing:**
- Operation: move vertices to improve tet quality
- Constraint: vertices cannot move outside envelope

**Stopping criteria:**
- `max_energy <= 10` and all input faces inserted
- Quality stops improving
- Reached 80-pass limit

Every 3rd pass, an additional triangle insertion step is performed.

### Step 5: Post-processing

- Final collapse pass for cleanup
- Winding number computation to determine inside vs outside
- Remove exterior tets
- Output `.msh` file

## Envelope Concept

The envelope is a "shell" of thickness epsilon around the input surface. All mesh operations (collapse, smooth) guarantee that surface vertices never move outside this shell. This is how fTetWild ensures the output is "shape-similar" to the input. Smaller epsilon = more faithful to original shape, but slower computation.

## Threshold Summary

| Parameter | Value | Computation | Purpose |
|-----------|-------|-------------|---------|
| `ideal_edge_length` | 5% bbox_diag | `bbox_diag * 0.05` | Target edge length |
| `epsilon` | 0.1% bbox_diag | `bbox_diag * 0.001` | Envelope thickness |
| `split_threshold` | 6.67% bbox_diag | `ideal_edge_length * 4/3` | Split edges longer than this |
| `collapse_threshold` | 4% bbox_diag | `ideal_edge_length * 4/5` | Collapse edges shorter than this |
| `min_edge_length` | 0.1% bbox_diag | `bbox_diag * eps_rel` | Minimum allowed edge length |

All thresholds are further scaled by a per-vertex `sizing_scalar` for adaptive meshing.

## Phase Transition Explanation

Understanding the pipeline explains the phase transition observed at `iel ≈ 0.01146` for the sphere19K mesh:

1. **Delaunay stage**: starts from ~4K vertices, largely independent of iel
2. **Pass 0 Splitting**: nearly all initial edges are much longer than `iel * 4/3`, triggering massive splitting → ~690K vertices
3. **Pass 0 Collapsing**: post-split edge lengths naturally fall around `iel * 2/3` (since splitting roughly halves edges), while the collapse threshold is `iel * 4/5`. When these two values are close, a tiny iel change pushes a large batch of edges across the collapse threshold
4. **Cascade**: collapsing is iterative (do-while loop in source) — each collapse modifies local topology, creates new short edges, triggers more collapses, until convergence

This is why iel=0.011465 → 0.01146 (a difference of 0.000005) causes #v to jump from 188K to 110K. See `docs/remesh_phase_transition.md` for detailed log analysis.
