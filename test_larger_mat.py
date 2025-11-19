print("hello")

import os
import re
import subprocess
import resource
import signal

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


def run_single_trial(exp_mat_name, exp_mat_dir, solver_name, bin_path, save_dir, timeout):
    os.makedirs(save_dir, exist_ok=True)
    pattern = re.compile(r'^\d+_\d+_A\.bin$')
    bin_list = [f for f in os.listdir(exp_mat_dir) if os.path.isfile(os.path.join(exp_mat_dir, f)) and pattern.match(f)]
    log_path = os.path.join(save_dir, solver_name+"_"+exp_mat_name+".log")
    open(log_path, 'w').close() 

    os.environ['OMP_NUM_THREADS'] = "1"

    for file in bin_list:
        A = os.path.join(exp_mat_dir, file)
        b = os.path.join(exp_mat_dir, file.split(".")[0][:-1]+"b.bin")

        cmd_string="%s %s %s %s"%(
            bin_path,
            A,
            b,
            solver_name)  

        code,msg,mem=run_cmd(cmd_string, timeout*60)  # timeout=30*60sec

        with open(log_path, 'a') as f:
            f.write("%s\ncode %d\nmemory_usage_mb %f\n%s\n"%(cmd_string,code,mem,msg))



solver_list = ["Eigen::PardisoLDLT", "Hypre", "AMGCL"]
mat_expnames = ["3D_golf_ball_vanilla_try_larger_matrix_0",
                "3D_golf_ball_39376_try_larger_matrix_0",
                "3D_golf_ball_73852_try_larger_matrix_0",
                "3D_golf_ball_113325_try_larger_matrix_1",
                "3D_golf_ball_189090_try_larger_matrix_2"]
mat_dirs = ["/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index/3D_golf_ball_vanilla_try_larger_matrix_0",
                "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index/3D_golf_ball_39376_try_larger_matrix_0",
                "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index/3D_golf_ball_73852_try_larger_matrix_0",
                "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index/3D_golf_ball_113325_try_larger_matrix_1",
                "/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index/3D_golf_ball_189090_try_larger_matrix_2"]
log_save_dir = "/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mat_exp_result/trial_2"
timeout = 30


for i, expname in enumerate(mat_expnames):
    for solver in solver_list:
        run_single_trial(exp_mat_name = expname
                         , exp_mat_dir = mat_dirs[i]
                         , solver_name = solver
                         , bin_path = polysolve_bin
                         , save_dir = log_save_dir
                         , timeout = timeout)
        print("Solver: ", solver, "Exp: ", expname)
