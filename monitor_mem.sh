#!/bin/bash
LOG="/u/1/chenyang/benchmark_data/larger_matrix_exp/polyfem_mem.log"

echo "timestamp,pid,rss_gb,command" | tee "$LOG"

while true; do
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    ps aux | grep PolyFEM | grep -v grep | awk -v ts="$ts" '{
        printf "%s,%s,%.2f,%s\n", ts, $2, $6/1024/1024, $NF
    }' | tee -a "$LOG"
    sleep 60
done
