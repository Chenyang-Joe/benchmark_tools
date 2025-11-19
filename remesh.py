print("hello")

import meshio
import igl
import numpy as np
import subprocess
import os

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
    mesh = meshio.Mesh(points=V, cells=cells, point_data=point_data)
    return mesh

raw_tet_path = "/u/1/chenyang/benchmark_data/larger_matrix_exp/contact/meshes/3D/simple/sphere/sphere19K.msh"
save_path = "/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mesh/"
new_sm_path = save_path + raw_tet_path.split("/")[-1].split(".")[0] + "_sf.obj"
new_tet_path = save_path + raw_tet_path.split("/")[-1].split(".")[0] + f"_new_tet.msh"
ftetwild_bin = "/u/1/chenyang/fTetWild/build/FloatTetwild_bin"
ideal_edge_length = 0.0105
# ideal_edge_length default 0.05, 0.017 should be good

# 0.0105 - > #v = 202243
# 0.011 - > #v = 189090
# 0.0115 - > #v = 113325
# the smallest granularity is 0.001

# stats raw tet
raw_tet = meshio.read(raw_tet_path)
raw_num_vertices = len(raw_tet.points)

# tet to surface mesh
new_sm = load_mesh(raw_tet_path)
new_sm.write(new_sm_path)

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
os.rename(new_tet_path, new_tet_path.split(".")[0]+f"_{new_num_vertices}.msh")


