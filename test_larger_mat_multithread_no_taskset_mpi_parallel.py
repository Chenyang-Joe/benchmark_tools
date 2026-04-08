print("hello")

import os
import re
import struct
import subprocess
import resource
import signal
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


_BIN_PATTERN = re.compile(r'^\d+_\d+_A\.bin$')


def get_first_bin_path(folder):
    """Return path to the smallest (outer, inner) A.bin in folder, or None."""
    bins = [f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f)) and _BIN_PATTERN.match(f)]
    if not bins:
        return None
    bins.sort(key=lambda x: (int(x.split("_")[0]), int(x.split("_")[1])))
    return os.path.join(folder, bins[0])


def get_mat_sz_from_bin(fp):
    """Read the matrix row count from a polysolve binary file.

    Mirrors libs/parser.py::get_mat_sz but uses stdlib struct (no numpy dep).
    Header layout:
        offset  0..11: 3 x int32 (dim, is_spd, is_sequence)
        offset 12..15: int32 format_check
            if format_check == -1 (POLYSOLVE_LARGE_INDEX):
                offset 16..23: int64 n_rows  (then cols, nnz, innS, outS)
            else:
                format_check itself is n_rows (legacy int32 layout)
    """
    try:
        with open(fp, 'rb') as f:
            f.seek(12)
            buf = f.read(4)
            if len(buf) < 4:
                return None
            format_check = struct.unpack('i', buf)[0]
            if format_check == -1:
                buf = f.read(8)
                if len(buf) < 8:
                    return None
                n_rows = struct.unpack('q', buf)[0]
            else:
                n_rows = format_check
            return int(n_rows)
    except Exception as e:
        print(f"get_mat_sz_from_bin error for {fp}: {e}")
        return None


def run_cmd(cmd_string, timeout=30*60, env=None):
    print(cmd_string)
    p = subprocess.Popen(cmd_string, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True, close_fds=True,
                         start_new_session=True, env=env)
    format = 'utf-8'

    memory_usage_mb = 0.0
    try:
        (msg, errs) = p.communicate(timeout=timeout)
        ret_code = p.poll()
        if ret_code:
            code = 1
            msg = "[Error]Called Error : " + str(msg.decode(format))
        else:
            code = 0
            msg = str(msg.decode(format))

            max_memory_bytes = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            memory_usage_mb = max_memory_bytes / 1024

    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)

        code = 1
        msg = "[TIMEOUT] after " + str(round(timeout/60)) + " min"

    except Exception as e:
        code = 1
        msg = "[ERROR]Unknown Error : " + str(e)

    return code, msg, memory_usage_mb


def run_single_trial(exp_mat_name, exp_mat_dir, solver_name, bin_path, save_dir, timeout, cores=None, threads=8, mini_batch_size=-1):
    os.makedirs(save_dir, exist_ok=True)
    pattern = re.compile(r'^\d+_\d+_A\.bin$')
    bin_list = [f for f in os.listdir(exp_mat_dir) if os.path.isfile(os.path.join(exp_mat_dir, f)) and pattern.match(f)]
    bin_list.sort(key=lambda x: (int(x.split("_")[0]), int(x.split("_")[1])))
    log_path = os.path.join(save_dir, solver_name + "_" + exp_mat_name + ".log")
    open(log_path, 'w').close()

    env = os.environ.copy()
    if solver_name in ("Trilinos", "Hypre_mpi"):
        env['OMP_NUM_THREADS'] = '1'
    else:
        env['OMP_NUM_THREADS'] = str(threads)

    for count, file in enumerate(bin_list):
        if mini_batch_size > 0 and count >= mini_batch_size:
            print("Skipping further tests for brevity.")
            break
        A = os.path.join(exp_mat_dir, file)
        b = os.path.join(exp_mat_dir, file.split(".")[0][:-1] + "b.bin")

        # Hypre_mpi passes "Hypre" as the actual solver name to the executable
        exe_solver_name = "Hypre" if solver_name == "Hypre_mpi" else solver_name

        if cores is not None:
            cmd_string = "taskset -c %s %s %s %s %s" % (cores, bin_path, A, b, exe_solver_name)
        elif solver_name in ("Trilinos", "Hypre_mpi"):
            cmd_string = "mpirun --oversubscribe -np %s %s %s %s %s" % (threads, bin_path, A, b, exe_solver_name)
        else:
            cmd_string = "%s %s %s %s" % (bin_path, A, b, exe_solver_name)

        code, msg, mem = run_cmd(cmd_string, timeout * 60, env=env)

        with open(log_path, 'a') as f:
            f.write("%s\ncode %d\nmemory_usage_mb %f\n%s\n" % (cmd_string, code, mem, msg))


def run_task(args):
    expname, exp_mat_dir, solver, polysolve_bin, log_save_dir, timeout, num_threads, mini_batch_size = args
    if solver in ("Trilinos", "Hypre_mpi"):
        print(f"[START] exp={expname} solver={solver} MPI_NP={num_threads} OMP_NUM_THREADS=1")
    else:
        print(f"[START] exp={expname} solver={solver} OMP_NUM_THREADS={num_threads}")
    run_single_trial(
        exp_mat_name=expname,
        exp_mat_dir=exp_mat_dir,
        solver_name=solver,
        bin_path=polysolve_bin,
        save_dir=log_save_dir,
        timeout=timeout,
        threads=num_threads,
        mini_batch_size=mini_batch_size,
    )
    print(f"[DONE]  exp={expname} solver={solver}")


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='Run larger matrix benchmarks with multithreading (parallel).')
    argparser.add_argument('--threads', type=int, default=8, help='Number of threads per solver.')
    argparser.add_argument('--num_workers', type=int, default=2, help='Number of parallel jobs.')
    argparser.add_argument('--data_name', type=str, default="golf_ball", help='Name of the dataset to use.')
    argparser.add_argument('--mini_batch_size', type=int, default=-1, help='Number of matrices to test per solver (for quick testing).')
    argparser.add_argument('--skip_direct_for_large', action=argparse.BooleanOptionalAction, default=True,
                           help='Skip direct solvers for folders whose first A.bin exceeds the reference mat_sz. '
                                'Default: enabled. Use --no-skip_direct_for_large to disable.')
    args = argparser.parse_args()
    data_name = args.data_name
    num_threads = args.threads
    num_workers = args.num_workers
    mini_batch_size = args.mini_batch_size
    skip_direct_for_large = args.skip_direct_for_large

    # solver_list = ["Eigen::PardisoLDLT", "Hypre", "AMGCL", "Trilinos"]
    # solver_list = ["Hypre", "Trilinos"]
    solver_list = ["Hypre_mpi", "AMGCL", "Trilinos", "Eigen::PardisoLDLT"]
    # solver_list = ["Eigen::PardisoLDLT"]

    # Direct solvers scale poorly to very large matrices. When enabled (the
    # default), we skip any folder whose first A.bin has more rows than the
    # threshold below. Iterative solvers are unaffected.
    DIRECT_SOLVERS = {
        "Eigen::PardisoLDLT",
        "Eigen::PardisoLLT",
        "Eigen::CholmodSupernodalLLT",
    }
    # Hardcoded from result_10000-2568220/242373/1_1_A.bin (mat_sz = 727119).
    # If you want to change the cutoff, pick another reference folder and read
    # its mat_sz with libs/parser.py::get_mat_sz, then update this constant.
    DIRECT_SOLVER_MAT_SZ_LIMIT = 730000
    if skip_direct_for_large:
        print(f"Direct-solver mat_sz limit: {DIRECT_SOLVER_MAT_SZ_LIMIT}")
    else:
        print("Direct-solver skip is DISABLED (--no-skip_direct_for_large)")

    if data_name == "old_data":
        mat_source_dir = "/mnt/hdd1/chenyang/benchmark_data/matrix_resource/solver-mat-0906"
    elif data_name == "golf_ball":
        mat_source_dir = "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/result_10000-2568220"

    mat_expnames = os.listdir(mat_source_dir)
    if data_name == "golf_ball":
        mat_expnames.sort(key=lambda x: int(x))

    mat_dirs = [os.path.join(mat_source_dir, exp_name) for exp_name in mat_expnames]

    polysolve_bin = "/u/1/chenyang/benchmark/build.trilinos_tpetra/TestMatLogger"
    log_save_dir = f"/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mat_exp_result/2026-4-8/10000-2568220/{data_name}_{num_threads}"
    timeout = 30

    # Build task list: (expname, mat_dir, solver, ...)
    # When skip_direct_for_large is enabled, skip direct solvers for any folder
    # whose first A.bin's mat_sz exceeds DIRECT_SOLVER_MAT_SZ_LIMIT.
    tasks = []
    for i, expname in enumerate(mat_expnames):
        # Only read mat_sz when we actually need it (skip is enabled).
        mat_sz = None
        if skip_direct_for_large:
            first_bin = get_first_bin_path(mat_dirs[i])
            mat_sz = get_mat_sz_from_bin(first_bin) if first_bin else None
        for solver in solver_list:
            if (skip_direct_for_large
                    and solver in DIRECT_SOLVERS
                    and mat_sz is not None
                    and mat_sz > DIRECT_SOLVER_MAT_SZ_LIMIT):
                print(f"[SKIP] exp={expname} solver={solver} "
                      f"(mat_sz={mat_sz} > {DIRECT_SOLVER_MAT_SZ_LIMIT})")
                continue
            tasks.append((expname, mat_dirs[i], solver, polysolve_bin, log_save_dir, timeout, num_threads, mini_batch_size))

    print(f"Total tasks: {len(tasks)}, running with {num_workers} parallel workers")

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(run_task, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] exp={task[0]} solver={task[2]}: {e}")

    print("All jobs finished.")
