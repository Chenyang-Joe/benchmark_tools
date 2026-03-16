# fTetWild Remesh Phase Transition Analysis

## Observation

When remeshing `sphere19K.msh` with fTetWild, varying `ideal_edge_length` (iel) from 0.010 to 0.015, the number of output vertices (#v) shows a sharp discontinuity around iel ≈ 0.01146-0.01148.

### Run 1 (test01145_01149_1)

| iel | #v |
|---|---|
| 0.01145 | 187,835 |
| 0.011455 | 187,948 |
| 0.011465 | 188,123 |
| **0.01146** | **110,217** |
| 0.01147 | 109,876 |
| 0.01148 | 109,684 |
| 0.01149 | 109,669 |

Transition: between iel=0.011465 and iel=0.01146.

### Run 2 (test01145_01149_2)

| iel | #v |
|---|---|
| 0.01145 | 187,790 |
| 0.011455 | 187,859 |
| 0.011465 | 187,773 |
| **0.01146** | **187,522** |
| **0.011475** | **109,739** |
| 0.01147 | 109,735 |
| 0.01148 | 109,546 |
| 0.01149 | 100,151 |

Transition: between iel=0.01146 and iel=0.011475.

### Broader range (test0)

| iel | #v |
|---|---|
| 0.0100 | 215,692 |
| 0.0105 | 203,092 |
| 0.0110 | 194,504 |
| 0.0115 | 109,463 |
| 0.0120 | 73,869 |
| 0.0125 | 66,521 |
| 0.0130 | 61,078 |
| 0.0135 | 56,766 |
| 0.0140 | 53,324 |
| 0.0145 | 50,460 |
| 0.0150 | 47,678 |

### Key findings

1. The jump is always from ~188K to ~110K (~70K gap, skipping 120K-180K range)
2. The exact transition point is **non-deterministic** — it shifts between runs (0.011465↔0.01146 in run 1, 0.01146↔0.011475 in run 2), likely due to fTetWild's parallel execution with TBB (128 threads) introducing non-determinism in operation ordering

## Post-Split Average Edge Length Estimation

### Data source

From fTetWild log output at **iel=0.011475 (run 2)**, which fell on the "collapse" side of the transition:

```
bbox_diag_length = 1.73159
ideal_edge_length = 0.01987

Pass 0 splitting:
  success = 687,259
  #v = 691,359
  #t = 3,845,347
  avg_energy = 5.31801  (AMIPS energy, 3.0 = perfect regular tet)

Pass 0 collapsing (first round):
  success = 408,995
  → #v dropped from 691,359 to 238,315
```

### Calculation

**Goal:** estimate the average edge length in the tet mesh immediately after Pass 0 splitting, and compare it to the collapse threshold.

**Step 1: Estimate meshed volume**

The sphere19K mesh has `bbox_diag = 1.73159`. Assuming a cube bounding box: side = `1.73159 / √3 ≈ 1.0`. fTetWild pads the bbox by `max(ideal_edge_length, 2*eps) = max(0.0199, 0.00347) ≈ 0.02` per side. The tet mesh fills this padded bounding box (interior/exterior filtering happens only in post-processing).

```
V_total ≈ (1.0 + 2 * 0.02)³ = 1.04³ ≈ 1.12
```

**Step 2: Regular tet edge length for this density**

A regular tetrahedron with edge length `a` has volume `a³√2/12`. With T = 3,845,347 tets filling V_total:

```
T × a³√2/12 = V_total
a = (12 × V_total / (T × √2))^(1/3)
a = (12 × 1.12 / (3,845,347 × 1.4142))^(1/3)
a = (13.44 / 5,439,393)^(1/3)
a = (2.471 × 10⁻⁶)^(1/3)
a ≈ 0.01352
```

This is a **lower bound** on the average edge length, because the regular tetrahedron maximizes volume for a given edge length. Real (non-regular) tets with the same volume have larger average edge lengths. The log shows `avg_energy = 5.32` (AMIPS), confirming the tets are significantly non-regular (3.0 = perfect). The actual average edge length is somewhere above 0.0135, but we cannot determine the exact correction factor from topology alone without dumping the actual edge lengths from the source code.

**Step 3: Compare with collapse threshold**

```
collapse_threshold = ideal_edge_length × 4/5
                   = 0.01987 × 0.8
                   = 0.01590
```

| Quantity | Value |
|---|---|
| Post-split average edge length (lower bound) | 0.0135 |
| Post-split average edge length (actual, estimated) | > 0.0135, likely near 0.015-0.016 |
| Collapse threshold | 0.01590 |

The collapse threshold sits very close to (or within) the post-split edge length distribution. A tiny shift in iel → tiny shift in collapse threshold → large change in how many edges fall below → cascade collapse.

## The Cascade Mechanism

### Log comparison: iel=0.01146 (→187K) vs iel=0.011475 (→110K), run 2

| | iel=0.01146 | iel=0.011475 |
|---|---|---|
| ideal_edge_length | 0.019844 | 0.01987 |
| collapse threshold | 0.015875 | 0.015896 |
| Pass 0 splits | 659,922 | 687,259 |
| #v after split | 664,002 | 691,359 |
| Pass 0 collapse round 1 | **246,094** | **408,995** |
| #v after Pass 0 collapse | **378,105** | **238,315** |
| Pass 1 splits | 69,677 | 223,032 |
| Final tet #v | 378,982 | 237,975 |
| Final output #v | 187,522 | 109,739 |

The collapse threshold differs by only **0.000021**, yet Pass 0 first-round collapses differ by ~163K (246K vs 409K). Edge collapsing is iterative (do-while loop in source code): each collapse changes local topology → creates new short edges → triggers more collapses → positive feedback cascade.

### Why the transition happens at iel ≈ 0.01146 specifically

This critical iel is specific to the sphere19K mesh geometry. At this iel, the post-split mesh density (690K vertices in the meshed volume) produces an edge length distribution where the collapse threshold sits at a tipping point. A different input mesh (different size, shape, or initial resolution) would have its transition at a different iel.

## Non-Determinism

The exact transition point varies between runs (0.011465 in run 1, 0.01146-0.011475 in run 2). This is because fTetWild uses TBB with 128 threads — parallel edge operations are processed in non-deterministic order, leading to slightly different intermediate mesh states and different cascade dynamics.

## Implications

- Meshes with #v in the ~120K-180K range cannot be obtained by tuning `iel` alone for this input mesh
- To get intermediate densities, consider:
  1. Two-pass remeshing: remesh to a very dense mesh first, extract surface, then remesh with larger iel (collapse-dominated, smoother behavior)
  2. Varying `--epsr` to shift the transition point
  3. Using a different input mesh resolution

## Experiment: Changing box_scale

### box_scale = 1/22

With denser initial grid (grid spacing = 1.73159/22 ≈ 0.0787):

| iel | #v |
|---|---|
| 0.0120 | 120,735 |
| 0.0125 | 116,751 |
| 0.0130 | 111,691 |
| 0.0135 | 106,189 |
| 0.0140 | 104,106 |
| 0.0145 | 102,930 |
| 0.0150 | 99,417 |
| **0.0155** | **36,164** |
| 0.0160 | 30,743 |

The 0.012-0.015 range became smooth, but a new phase transition appeared at iel ≈ 0.0155.

### Edge length dump verification

We added edge length dumping to fTetWild source code (MeshImprovement.cpp) to capture the full edge length distribution after Pass 0 splitting. Key data:

| | iel=0.015 (→99K) | iel=0.0155 (→36K) |
|---|---|---|
| split_threshold | 0.03463 | 0.03579 |
| before_split edges | 36,472 | 35,896 |
| **after_split edges** | **2,015,204** | **1,335,999** |
| split multiplier | **55.3x** | **37.2x** |

The initial meshes are nearly identical (~36K edges), but after splitting, iel=0.015 has 680K more edges.

### Histogram reveals the cause

Post-split edge length histogram (0.001 bins) around the split threshold:

```
iel=0.015 (split_thr=0.03463):
  [0.017-0.018):   757,763  ← products from splitting the 0.035-0.036 edges
  [0.020-0.021):   396,314
  [0.028-0.029):   314,481
  [0.034-0.035):     5,474  ← split_thr is here
  [0.035-0.036):         0  ← all split

iel=0.0155 (split_thr=0.03579):
  [0.017-0.018):    26,283  ← no products (parent edges weren't split)
  [0.020-0.021):   391,150
  [0.028-0.029):   314,022
  [0.034-0.035):     8,616
  [0.035-0.036):    94,956  ← NOT split (below threshold) ← split_thr is here
```

**94,956 cross edges** sit in the [0.035-0.036) bin. These are edges created by the first round of splitting (connecting midpoints to adjacent tet vertices).

- At iel=0.015 (split_thr=0.03463): these edges exceed the threshold → get split → produce 757K new edges at [0.017-0.018), plus additional cross edges → total 680K more edges
- At iel=0.0155 (split_thr=0.03579): these edges are below the threshold → not split → the entire cascade doesn't happen

The rest of the distribution is nearly identical between the two cases ([0.020-0.021) and [0.028-0.029) peaks match within 1%), confirming that the 95K cross edges in [0.035-0.036) are the sole cause of the divergence.

### Two types of phase transitions

| | box_scale=1/15 (original) | box_scale=1/22 |
|---|---|---|
| Grid spacing | 0.1154 | 0.0787 |
| Transition at | iel ≈ 0.01146 | iel ≈ 0.0155 |
| Mechanism | **Collapse cascade**: post-multi-split edges cluster near collapse threshold | **Split cascade**: post-first-split cross edges cluster near split threshold |
| Where in pipeline | Pass 0 collapsing | Pass 0 splitting |
| Root cause | grid_spacing/2^n ≈ collapse_threshold | grid_spacing/2 cross edges ≈ split_threshold |

Both are caused by the same fundamental phenomenon: splitting creates edges at characteristic lengths (grid_spacing/2^n and cross edges), and whenever a threshold sweeps through a dense region of these characteristic lengths, a small parameter change causes a large change in mesh density.

### Conclusion

Changing `box_scale` moves the phase transition location but cannot eliminate it. The splitting process inherently creates edge length distributions with peaks at characteristic lengths tied to the grid spacing. Any `box_scale` will have some iel where a threshold coincides with one of these peaks.

## Raw Logs

### iel=0.01146 (run 2, → 187,522 vertices, "dense" side)

```
TBB threads 128
bbox_diag_length = 1.73159
ideal_edge_length = 0.019844
stage = 2
eps_input = 0.00173159
eps = 0.000958589
eps_simplification = 0.000766871
eps_coplanar = 1.73159e-06
dd = 0.00115439
dd_simplification = 0.000923513
collapsing 1.43139
swapping 0.016643

initializing...
edge collapsing...
success(env) = 2547, success = 2812(4967)
success(env) = 105, success = 129(537)
success(env) = 3, success = 5(84)
success(env) = 0, success = 0(8)
edge collapsing done! time = 0.317761s
#v = 4080, #t = 20644
max_energy = 5700.48, avg_energy = 16.6196

//////////////// pass 0 ////////////////
edge splitting...
success = 659922(659922)
edge splitting done! time = 3.52757s
#v = 664002, #t = 3693465
max_energy = 5700.48, avg_energy = 5.59271

edge collapsing...
success(env) = 4436, success = 246094(3046597)
success(env) = 721, success = 29165(480810)
success(env) = 143, success = 7362(218473)
success(env) = 58, success = 2069(88877)
success(env) = 20, success = 742(29686)
success(env) = 8, success = 303(11609)
success(env) = 2, success = 120(4919)
success(env) = 0, success = 29(1851)
success(env) = 0, success = 12(449)
success(env) = 0, success = 1(184)
success(env) = 0, success = 0(22)
edge collapsing done! time = 36.6791s
#v = 378105, #t = 2186182
max_energy = 656.75, avg_energy = 4.0043

edge swapping...
success3 = 11973, success4 = 403708, success5 = 4258
success = 419939(1820310)
edge swapping done! time = 29.0925s
#v = 378105, #t = 2178467
max_energy = 519.96, avg_energy = 3.44983

vertex smoothing...
success = 204965(347852)
vertex smoothing done! time = 2.769s
#v = 378105, #t = 2178467
max_energy = 49.287, avg_energy = 3.32557

//////////////// pass 1 ////////////////
edge splitting...
success = 69677(69677)
edge splitting done! time = 4.09214s
#v = 447782, #t = 2521314
max_energy = 49.287, avg_energy = 3.43922

edge collapsing...
success(env) = 1938, success = 59856(2378012)
success(env) = 152, success = 3380(279545)
success(env) = 15, success = 374(40377)
success(env) = 0, success = 82(5312)
success(env) = 1, success = 19(1153)
success(env) = 0, success = 4(210)
success(env) = 0, success = 0(71)
edge collapsing done! time = 23.4896s
#v = 384067, #t = 2209043
max_energy = 7.80831, avg_energy = 3.33609

edge swapping...
success = 28947(1407544)
edge swapping done! time = 16.4863s
#v = 384067, #t = 2208413
max_energy = 6.18987, avg_energy = 3.32848

vertex smoothing...
success = 305973(354809)
vertex smoothing done! time = 2.05587s
#v = 384067, #t = 2208413
max_energy = 6.07721, avg_energy = 3.28626

//////////////// postprocessing ////////////////
edge collapsing...
success(env) = 222, success = 4748(2134996)
success(env) = 12, success = 295(49070)
success(env) = 1, success = 39(3480)
success(env) = 0, success = 3(553)
success(env) = 0, success = 0(46)
edge collapsing done! time = 16.5697s
#v = 378982, #t = 2180647
max_energy = 6.05692, avg_energy = 3.28182

Num of vertices before:  28833
Num of vertices now:  187522
```

### iel=0.011475 (run 2, → 109,739 vertices, "sparse" side)

```
TBB threads 128
bbox_diag_length = 1.73159
ideal_edge_length = 0.01987
stage = 2
eps_input = 0.00173159
eps = 0.000958589
eps_simplification = 0.000766871
eps_coplanar = 1.73159e-06
dd = 0.00115439
dd_simplification = 0.000923513
collapsing 1.43887
swapping 0.016559

initializing...
edge collapsing...
success(env) = 2575, success = 2819(4933)
success(env) = 102, success = 129(414)
success(env) = 0, success = 2(71)
success(env) = 0, success = 0(0)
edge collapsing done! time = 0.329096s
#v = 4100, #t = 20848
max_energy = 2092.55, avg_energy = 14.9497

//////////////// pass 0 ////////////////
edge splitting...
success = 687259(687259)
edge splitting done! time = 3.865s
#v = 691359, #t = 3845347
max_energy = 2092.55, avg_energy = 5.31801

edge collapsing...
success(env) = 4398, success = 408995(2102431)
success(env) = 710, success = 33011(592857)
success(env) = 141, success = 7323(221443)
success(env) = 53, success = 2269(81120)
success(env) = 28, success = 874(29238)
success(env) = 9, success = 335(11393)
success(env) = 1, success = 142(4489)
success(env) = 0, success = 52(1945)
success(env) = 0, success = 17(774)
success(env) = 0, success = 6(317)
success(env) = 0, success = 7(97)
success(env) = 0, success = 6(162)
success(env) = 0, success = 6(122)
success(env) = 0, success = 1(106)
success(env) = 0, success = 0(10)
edge collapsing done! time = 34.7827s
#v = 238315, #t = 1302242
max_energy = 357.341, avg_energy = 3.99546

edge swapping...
success3 = 12687, success4 = 73574, success5 = 4602
success = 90863(1082522)
edge swapping done! time = 15.7907s
#v = 238315, #t = 1294157
max_energy = 98.1915, avg_energy = 3.86307

vertex smoothing...
success = 167323(216004)
vertex smoothing done! time = 1.54913s
#v = 238315, #t = 1294157
max_energy = 28.2467, avg_energy = 3.6553

//////////////// pass 1 ////////////////
edge splitting...
success = 223032(223032)
edge splitting done! time = 2.67917s
#v = 461347, #t = 2569853
max_energy = 26.5938, avg_energy = 3.8812

edge collapsing...
success(env) = 2018, success = 206223(1470056)
success(env) = 130, success = 5631(439629)
success(env) = 19, success = 634(55078)
success(env) = 1, success = 134(7753)
success(env) = 0, success = 28(1476)
success(env) = 0, success = 5(303)
success(env) = 0, success = 0(42)
edge collapsing done! time = 23.0109s
#v = 248692, #t = 1351639
max_energy = 7.15463, avg_energy = 3.67287

edge swapping...
success = 33653(1034758)
edge swapping done! time = 12.2342s
#v = 248692, #t = 1351068
max_energy = 6.13693, avg_energy = 3.65513

vertex smoothing...
success = 208726(225721)
vertex smoothing done! time = 2.37184s
#v = 248692, #t = 1351068
max_energy = 6.01218, avg_energy = 3.56804

//////////////// postprocessing ////////////////
edge collapsing...
success(env) = 187, success = 10076(427081)
success(env) = 6, success = 566(76504)
success(env) = 1, success = 64(5258)
success(env) = 0, success = 10(617)
success(env) = 0, success = 1(119)
success(env) = 0, success = 0(11)
edge collapsing done! time = 8.0112s
#v = 237975, #t = 1292519
max_energy = 5.8421, avg_energy = 3.55852

Num of vertices before:  28833
Num of vertices now:  109739
```
