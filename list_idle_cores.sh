#!/bin/bash

# Script to list idle CPU cores based on their current usage

echo "Checking CPU core usage..."
echo "=========================="

# Get CPU usage per core using mpstat (if available)
if command -v mpstat &> /dev/null; then
    echo -e "\nUsing mpstat to check core usage (1 second sample):\n"
    
    # Run mpstat for 1 second, parse output to show idle cores
    mpstat -P ALL 1 1 | awk '
        /Average:/ && $2 ~ /^[0-9]+$/ {
            cpu=$2
            idle=$NF
            if (idle > 95.0) {
                printf "Core %3s: %.2f%% idle (IDLE)\n", cpu, idle
            } else if (idle > 50.0) {
                printf "Core %3s: %.2f%% idle (lightly used)\n", cpu, idle
            } else {
                printf "Core %3s: %.2f%% idle (BUSY)\n", cpu, idle
            }
        }
    '
    
    echo -e "\n=== Idle cores (>95% idle) ==="
    mpstat -P ALL 1 1 | awk '/Average:/ && $2 ~ /^[0-9]+$/ && $NF > 95.0 {printf "%s ", $2}' 
    echo -e "\n\n=== Busy cores (<50% idle) ==="
    mpstat -P ALL 1 1 | awk '/Average:/ && $2 ~ /^[0-9]+$/ && $NF < 50.0 {printf "%s ", $2}'
    echo -e "\n"
    
# Fallback to top if mpstat is not available
elif command -v top &> /dev/null; then
    echo -e "\nmpstat not found, using top (less accurate):\n"
    echo "Install sysstat for better per-core monitoring: sudo apt install sysstat"
    top -bn2 -d 0.5 | grep "Cpu(s)" | tail -1
    
else
    echo "Neither mpstat nor top found. Please install sysstat:"
    echo "  sudo apt install sysstat"
fi

# Show total number of cores
echo -e "\nTotal CPU cores: $(nproc)"
echo "Physical cores: $(lscpu | grep "Core(s) per socket" | awk '{print $4}')"
echo "Sockets: $(lscpu | grep "Socket(s)" | awk '{print $2}')"
