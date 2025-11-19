import meshio

# mesh_path = "/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mesh/sphere19K_new_tet_189090.msh"
mesh_path = "/u/1/chenyang/benchmark_data/larger_matrix_exp/contact/meshes/3D/simple/sphere/sphere19K.msh"
mesh = meshio.read(mesh_path)
num_vertices = len(mesh.points)

print("Num of vertices: ", num_vertices)
