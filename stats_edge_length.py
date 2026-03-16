import meshio
import igl
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def get_surface_edge_lengths(mesh_path):
    mesh = meshio.read(mesh_path)
    V = mesh.points
    for cells in mesh.cells:
        if cells.type == "tetra":
            F = igl.boundary_facets(cells.data)
            if isinstance(F, tuple):
                F = F[0]
            return igl.edge_lengths(V, F)
        elif cells.type == "triangle":
            return igl.edge_lengths(V, cells.data)
    raise ValueError(f"No tetra or triangle cells found in {mesh_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh_path", help="Path to .msh or .obj file")
    parser.add_argument("--bins", type=int, default=100)
    args = parser.parse_args()

    mesh_path = Path(args.mesh_path)
    lengths = get_surface_edge_lengths(str(mesh_path))

    print(f"Edge length stats for {mesh_path.name}:")
    print(f"  mean:   {lengths.mean():.6f}")
    print(f"  median: {np.median(lengths):.6f}")
    print(f"  std:    {lengths.std():.6f}")
    print(f"  min:    {lengths.min():.6f}")
    print(f"  max:    {lengths.max():.6f}")

    save_dir = Path("/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mesh/dataset_curation")
    save_path = save_dir / f"{mesh_path.stem}_edge_length_hist.png"

    plt.figure()
    plt.hist(lengths.flatten(), bins=args.bins, edgecolor="black", linewidth=0.5)
    plt.axvline(lengths.mean(), color="r", linestyle="--", label=f"mean={lengths.mean():.5f}")
    plt.axvline(np.median(lengths), color="orange", linestyle="--", label=f"median={np.median(lengths):.5f}")
    plt.xlabel("Edge Length")
    plt.ylabel("Count")
    plt.title(f"Edge Length Distribution: {mesh_path.name}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    print(f"Saved to {save_path}")
