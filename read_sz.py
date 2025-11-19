import numpy as np

def get_mat_sz(fp):
    try:
        # the first 8 values are: dim, is_spd, is_sequence, nrow, ncol, nnz, outer_sz, inner_sz
        # nnz, number of non-zero element
        meta = np.fromfile(fp, dtype=np.int32, count=8, offset=0)
        n_rows = meta[3]
        return n_rows
    except:
        print("mat size exception")
        return None

bin_file = "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin/3D_golf_ball_113325_CholmodSupernodalLLT/1_15_A.bin"
print(get_mat_sz(bin_file))