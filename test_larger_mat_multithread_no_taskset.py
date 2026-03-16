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
            memory_usage_mb = max_memory_bytes / (1024 * 1024) 

    except subprocess.TimeoutExpired:
        # 注意：不能使用p.kill和p.terminate，无法杀干净所有的子进程，需要使用os.killpg
        p.kill()
        p.terminate()
        os.killpg(p.pid, signal.SIGUSR1)
 
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


def run_single_trial(exp_mat_name, exp_mat_dir, solver_name, bin_path, save_dir, timeout, cores = None, threads = 8):
    os.makedirs(save_dir, exist_ok=True)
    pattern = re.compile(r'^\d+_\d+_A\.bin$')
    bin_list = [f for f in os.listdir(exp_mat_dir) if os.path.isfile(os.path.join(exp_mat_dir, f)) and pattern.match(f)]
    log_path = os.path.join(save_dir, solver_name+"_"+exp_mat_name+".log")
    open(log_path, 'w').close() 

    os.environ['OMP_NUM_THREADS'] = str(threads)

    # count = -1
    for file in bin_list:
        # count += 1
        # if count == 20:
        #     print("Skipping further tests for brevity.")
        #     break
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
    args = argparser.parse_args()
    data_name = args.data_name
    num_threads = args.threads

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
    
    polysolve_bin = "/u/1/chenyang/benchmark/build.multithread_pardiso/TestMatLogger"

    log_save_dir = f"/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mat_exp_result/2026-1-14/all_together/{data_name}_{num_threads}"
    timeout = 30



    for i, expname in enumerate(mat_expnames):
        for solver in solver_list:
            os.environ['OMP_NUM_THREADS'] = str(num_threads)
            # os.environ['MKL_NUM_THREADS'] = str(num_threads)
            # echo to check if the env is set correctly
            print("OMP_NUM_THREADS:", os.environ['OMP_NUM_THREADS'])
            # print("MKL_NUM_THREADS:", os.environ['MKL_NUM_THREADS'])
            run_single_trial(exp_mat_name = expname
                            , exp_mat_dir = mat_dirs[i]
                            , solver_name = solver
                            , bin_path = polysolve_bin
                            , save_dir = log_save_dir
                            , timeout = timeout,
                            threads = num_threads)  # Use 32 CPU cores
            print("Solver: ", solver, "Exp: ", expname)
