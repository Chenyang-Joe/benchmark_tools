print("hello")

import meshio
import igl
import numpy as np
import subprocess
import os
import argparse
from pathlib import Path

def load_mesh(path):
    mesh = meshio.read(path)
    V, I, J = igl.remove_duplicate_vertices(
        mesh.points, 1e-7)
    CV = []  # codim vertices
    E = []  # edges
    F = []  # triangles
    for cells in mesh.cells:
        if cells.type == "triangle":
            F.append(J[cells.data])
        elif cells.type == "tetra":
            boundary = igl.boundary_facets(J[cells.data])
            if isinstance(boundary, tuple):
                boundary = boundary[0]
            F.append(boundary)
            F[-1] = F[-1][:, ::-1]  # flip triangles
        elif cells.type == "line":
            E.append(J[cells.data])
        elif cells.type == "vertex":
            CV.append(J[cells.data])
        else:
            raise Exception("Unsupported cell type: {}".format(cells.type))
    cells = []
    if F:
        cells.append(("triangle", np.vstack(F).astype("int32")))
    if E:
        cells.append(("line", np.vstack(E).astype("int32")))
    if CV:
        cells.append(("vertex", np.vstack(CV).astype("int32")))
    if "solution" in mesh.point_data:
        V += mesh.point_data["solution"][I]
    point_data = {key: value[I] for key, value in mesh.point_data.items()}
    # remove unreferenced vertices
    all_indices = np.concatenate([c[1].flatten() for c in cells])
    referenced = np.unique(all_indices)
    new_idx = np.full(len(V), -1, dtype=int)
    new_idx[referenced] = np.arange(len(referenced))
    V = V[referenced]
    point_data = {key: value[referenced] for key, value in point_data.items()}
    cells = [(ctype, new_idx[cdata]) for ctype, cdata in cells]
    mesh = meshio.Mesh(points=V, cells=cells, point_data=point_data)
    return mesh

if __name__ == "__main__":
    raw_tet_path = "/u/1/chenyang/benchmark_data/larger_matrix_exp/contact/meshes/3D/simple/sphere/sphere19K.msh"
    save_path = Path("/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mesh/dataset_curation/result_10")
    ftetwild_bin = "/u/1/chenyang/fTetWild/build.box_scale_10/FloatTetwild_bin"
    parse = argparse.ArgumentParser(description='Remesh a tet mesh with fTetWild.')
    parse.add_argument('--ideal_edge_length', type=float, default=0.0105, help='Ideal edge length for remeshing.')
    args = parse.parse_args()
    ideal_edge_length = args.ideal_edge_length
    mesh_name = raw_tet_path.split("/")[-1].split(".")[0]
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    new_sm_path = save_path / (mesh_name + "_sf.obj")
    new_tet_path = save_path / (mesh_name + f"_iel{ideal_edge_length}_new_tet.msh")

    # ideal_edge_length default 0.05, 0.017 should be good

    # 0.0105 - > #v = 202243
    # 0.011 - > #v = 189090
    # 0.0115 - > #v = 113325
    # the smallest granularity is 0.001 (not really)

    # stats raw tet
    raw_tet = meshio.read(raw_tet_path)
    raw_num_vertices = len(raw_tet.points)

    # tet to surface mesh
    if not os.path.exists(new_sm_path):
        new_sm = load_mesh(raw_tet_path)
        new_sm.write(new_sm_path)
    else:
        print("Surface mesh already exists, skipping tet to surface conversion.")

    # surface mesh to tet
    cmd = [
        ftetwild_bin,
        "-i", new_sm_path,
        "-o", new_tet_path,
        "-l", str(ideal_edge_length),
        "--no-binary",
        "--no-color"
    ]
    result = subprocess.run(cmd)

    # stats new tet
    new_tet = meshio.read(new_tet_path)
    new_num_vertices = len(new_tet.points)

    print("Num of vertices before: ", raw_num_vertices) #28833
    print("Num of vertices now: ", new_num_vertices) 
    print(ideal_edge_length)
    print("Done!")
    # rename the new tet file to include the number of vertices in the filename
    base, ext = os.path.splitext(new_tet_path)
    os.rename(new_tet_path, f"{base}_nv{new_num_vertices}{ext}")


