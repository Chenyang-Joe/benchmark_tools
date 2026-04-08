import numpy as np

def get_mat_sz(fp):
    try:
        # header: dim, is_spd, is_sequence, flags (4x int32), then nrow, ncol, nnz, ... (int64)
        n_rows = np.fromfile(fp, dtype=np.int64, count=1, offset=16)[0]
        return n_rows
    except:
        print("mat size exception")
        return None

bin_file = "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/result_250000_plus_2/1124010/1_1_A.bin"
print(get_mat_sz(bin_file))