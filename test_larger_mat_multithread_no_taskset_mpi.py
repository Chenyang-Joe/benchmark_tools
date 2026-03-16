# the correct one to run
print("hello")

import os
import re
import subprocess
import resource
import signal

import argparse

def run_cmd(cmd_string, timeout=30*60):

    print(cmd_string)
    p = subprocess.Popen(cmd_string, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True, close_fds=True,
                         start_new_session=True)
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
            
            # Get the memory usage of the subprocess
            max_memory_bytes = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            memory_usage_mb = max_memory_bytes / 1024  # ru_maxrss is in KB on Linux

    except subprocess.TimeoutExpired:
        # 注意：不能使用p.kill和p.terminate，无法杀干净所有的子进程，需要使用os.killpg
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
 
        # 注意：如果开启下面这两行的话，会等到执行完成才报超时错误，但是可以输出执行结果
        # (outs, errs) = p.communicate()
        # print(outs.decode('utf-8'))
 
        code = 1
        msg = "[TIMEOUT] after " + str(round(timeout/60)) + " min"

    except Exception as e:
        code = 1
        msg = "[ERROR]Unknown Error : " + str(e)
 
    # print(msg)
    return code, msg, memory_usage_mb


def run_single_trial(exp_mat_name, exp_mat_dir, solver_name, bin_path, save_dir, timeout, cores = None, threads = 8, mini_batch_size = -1):
    os.makedirs(save_dir, exist_ok=True)
    pattern = re.compile(r'^\d+_\d+_A\.bin$')
    bin_list = [f for f in os.listdir(exp_mat_dir) if os.path.isfile(os.path.join(exp_mat_dir, f)) and pattern.match(f)]
    log_path = os.path.join(save_dir, solver_name+"_"+exp_mat_name+".log")
    open(log_path, 'w').close() 

    if solver_name == "Trilinos":
        # MPI parallelism: each MPI rank should use 1 thread to avoid oversubscription
        os.environ['OMP_NUM_THREADS'] = '1'
    else:
        os.environ['OMP_NUM_THREADS'] = str(threads)

    for count, file in enumerate(bin_list):
        if mini_batch_size > 0 and count >= mini_batch_size:
            print("Skipping further tests for brevity.")
            break
        A = os.path.join(exp_mat_dir, file)
        b = os.path.join(exp_mat_dir, file.split(".")[0][:-1]+"b.bin")

        # Use taskset to limit Pardiso to a single physical core (2 hyperthreads: CPU 0,64)
        # This creates a fair single-threaded comparison environment
        if cores is not None:
            cmd_string="taskset -c %s %s %s %s %s"%(
                cores,
                bin_path,
                A,
                b,
                solver_name)
        elif solver_name == "Trilinos":
            # Use mpirun to run Trilinos with the specified number of threads
            cmd_string="mpirun --oversubscribe -np %s %s %s %s %s"%(
                threads,
                bin_path,
                A,
                b,
                solver_name)
        else:
            cmd_string="%s %s %s %s"%(
                bin_path,
                A,
                b,
                solver_name)  

        code,msg,mem=run_cmd(cmd_string, timeout*60)  # timeout=30*60sec

        with open(log_path, 'a') as f:
            f.write("%s\ncode %d\nmemory_usage_mb %f\n%s\n"%(cmd_string,code,mem,msg))


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='Run larger matrix benchmarks with multithreading.')
    argparser.add_argument('--threads', type=int, default=8, help='Number of threads to use for the solver.')
    argparser.add_argument('--data_name', type=str, default="old_data", help='Name of the dataset to use.')
    argparser.add_argument('--mini_batch_size', type=int, default=-1, help='Number of matrices to test for each solver (for quick testing).')
    args = argparser.parse_args()
    data_name = args.data_name
    num_threads = args.threads
    mini_batch_size = args.mini_batch_size

    solver_list = ["Eigen::PardisoLDLT", "Hypre", "AMGCL", "Trilinos"]
    # solver_list = ["Eigen::PardisoLDLT"]

    if data_name == "old_data":
        mat_source_dir = "/mnt/hdd1/chenyang/benchmark_data/matrix_resource/solver-mat-0906"
    elif data_name == "golf_ball":
        mat_source_dir = "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index"
    mat_expnames = []
    mat_dirs = []
    for exp_name in os.listdir(mat_source_dir):
        mat_expnames.append(exp_name)
        mat_dirs.append(os.path.join(mat_source_dir, exp_name))
    
    polysolve_bin = "/u/1/chenyang/benchmark/build.trilinos_tpetra/TestMatLogger"

    log_save_dir = f"/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mat_exp_result/2026-3-11/full_run/{data_name}_{num_threads}"
    timeout = 30



    for i, expname in enumerate(mat_expnames):
        for solver in solver_list:
            if solver == "Trilinos":
                print("MPI_NP:", num_threads, "OMP_NUM_THREADS: 1")
            else:
                print("OMP_NUM_THREADS:", num_threads)
            run_single_trial(exp_mat_name = expname
                            , exp_mat_dir = mat_dirs[i]
                            , solver_name = solver
                            , bin_path = polysolve_bin
                            , save_dir = log_save_dir
                            , timeout = timeout
                            , threads = num_threads
                            , mini_batch_size = mini_batch_size
                            )
            print("Solver:", solver, "Exp:", expname)