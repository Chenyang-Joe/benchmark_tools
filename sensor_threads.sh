# every 0.1 sec, print thread usage of testmatlogger
# pid=$(pgrep -f TestMatLogger) && ps -T -p $pid | wc -l
while true; do
    pid=$(pidof /u/1/chenyang/benchmark/build.final_large_matrix.control_threads/TestMatLogger)
    if [ -n "$pid" ]; then
        thread_count=$(ps -T -p $pid | wc -l)
        echo "Thread count for TestMatLogger (PID: $pid): $((thread_count - 1))"
    else
        echo "TestMatLogger process not found."
    fi
    sleep 0.1
done