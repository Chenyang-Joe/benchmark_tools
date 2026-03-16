#!/bin/bash

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
for l in $list; do
    if [ "$l" = "$last" ]; then
        continue
    fi
    python -u remesh.py --ideal_edge_length $l > "tmp/remesh_$l.log" 2>&1 &
done

wait
echo "All remeshing jobs done."
