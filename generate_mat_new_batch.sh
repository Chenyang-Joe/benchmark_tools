#!/bin/bash
NUM_THREADS=32
export MKL_THREADING_LAYER=GNU
export MKL_NUM_THREADS=$NUM_THREADS
export OMP_NUM_THREADS=$NUM_THREADS

MESH_DIR="/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mesh/dataset_curation/result-2568220-plus"
BIN_FILE="/u/1/chenyang/LearnPolyFEM/polyfem/build.final_large_matrix_log_solver/PolyFEM_bin"
JSON_FILE="/u/1/chenyang/benchmark_data/larger_matrix_exp/contact/examples/3D/golf-ball_closer.json"
MAX_PARALLEL=1 # number of parallel jobs
TARGET_ITERS=6  # number of complete iterations to keep per mesh

run_one() {
    local MESH_NAME="$1"
    local NV=$(echo "$MESH_NAME" | grep -oP 'nv\K\d+')

    # Absolute path to target folder
    local target_folder="/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/result-2568220-plus/$NV"
    mkdir -p "$target_folder"

    local debug_log_file="$target_folder/debug_log.txt"
    touch "$debug_log_file"

    # Save modified JSON at original location with renamed name: {original}_{NV}_{mesh_dir_folder}.json
    local json_dir=$(dirname "$JSON_FILE")
    local json_base=$(basename "$JSON_FILE" .json)
    local mesh_dir_folder=$(basename "$MESH_DIR")
    local source_json="$json_dir/${json_base}_${NV}_${mesh_dir_folder}.json"
    jq --arg mesh "$MESH_NAME" '.geometry[0].mesh = $mesh' "$JSON_FILE" > "$source_json"

    # Copy common.json if referenced
    local common_name=$(jq -r '.common' "$JSON_FILE")
    if [ "$common_name" != "null" ]; then
        local common_path="$json_dir/$common_name"
        cp "$common_path" "$target_folder"
    fi

    # Copy the modified JSON to target folder
    cp "$source_json" "$target_folder"

    # Skip if TARGET_ITERS complete iterations already reached
    local iter_count
    iter_count=$(ls "$target_folder"/*_A.bin 2>/dev/null | wc -l)
    if [ "$iter_count" -ge "$TARGET_ITERS" ]; then
        echo "[$(date '+%H:%M:%S')] SKIP  nv=$NV ($TARGET_ITERS iterations already reached)"
        return
    fi

    echo "[$(date '+%H:%M:%S')] START nv=$NV mesh=$(basename "$MESH_NAME")"

    "$BIN_FILE" \
        --json "$source_json" \
        --mat_dir "$target_folder" \
        --max_threads $NUM_THREADS \
        > "$debug_log_file" 2>&1 &
    local pid=$!

    # Wait until TARGET_ITERS _A.bin and _b.bin both exist
    while kill -0 "$pid" 2>/dev/null; do
        local a_count b_count
        a_count=$(ls "$target_folder"/*_A.bin 2>/dev/null | wc -l)
        b_count=$(ls "$target_folder"/*_b.bin 2>/dev/null | wc -l)
        if [ "$a_count" -ge "$TARGET_ITERS" ] && [ "$b_count" -ge "$TARGET_ITERS" ]; then
            echo "[$(date '+%H:%M:%S')] WAIT  nv=$NV ($TARGET_ITERS iterations done, waiting 60s for IO)"
            sleep 60
            echo "[$(date '+%H:%M:%S')] STOP  nv=$NV (killing process)"
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
            break
        fi
        sleep 5
    done

    echo "[$(date '+%H:%M:%S')] DONE  nv=$NV"
}

export -f run_one
export BIN_FILE JSON_FILE MESH_DIR NUM_THREADS TARGET_ITERS

# Run all msh files in parallel, sorted by nv descending
find "$MESH_DIR" -name "*.msh" | sed 's/.*_nv\([0-9]*\).*/\1 &/' | sort -rn | cut -d' ' -f2 | xargs -P "$MAX_PARALLEL" -I {} bash -c 'run_one "$@"' _ {}
echo "All jobs finished."
