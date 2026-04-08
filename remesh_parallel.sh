#!/bin/bash

MAX_PARALLEL=1  # max number of parallel remesh jobs

if [ $# -ne 3 ]; then
    echo "Usage: $0 lower_bound upper_bound interval"
    echo "Example: $0 0.0100 0.0160 0.0005"
    exit 1
fi

lower=$1
upper=$2
interval=$3

# Generate list of iel values
list=$(python3 -c "
import numpy as np
vals = np.arange($lower, $upper + $interval/2, $interval)
print(' '.join(f'{v:.4f}' for v in vals))
")

echo "Will run with iel values: $list"

# First run the largest iel to generate the surface mesh (fastest, needed by all subsequent runs)
last=$(echo $list | awk '{print $NF}')
python remesh.py --ideal_edge_length $last
echo "Surface mesh generated, starting parallel runs..."

# Parallel remeshing (skip the last one since it's already done)
run_one() {
    local l=$1
    python -u remesh.py --ideal_edge_length $l > "tmp/remesh_$l.log" 2>&1
}
export -f run_one

# Filter out the last value and run with limited parallelism
for l in $list; do
    if [ "$l" = "$last" ]; then
        continue
    fi
    echo $l
done | xargs -P "$MAX_PARALLEL" -I {} bash -c 'run_one "$@"' _ {}

echo "All remeshing jobs done."
