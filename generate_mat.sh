#!/bin/bash
# export MKL_NUM_THREADS=1
export MKL_THREADING_LAYER=GNU
# export MKL_THREADING_LAYER=INTEL

TARGET_FOLDER="3D_golf_ball_113325_try_larger_matrix_1"
BIN_FILE="/u/1/chenyang/LearnPolyFEM/polyfem/build.final_large_matrix/PolyFEM_bin"
JSON_FILE="/u/1/chenyang/benchmark_data/larger_matrix_exp/contact/examples/3D/golf-ball_113325.json"

# Absolute path to target folder
target_folder="/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/new_mat_bin_support_large_index/${TARGET_FOLDER}"
# Create target folder if it does not exist
mkdir -p "$target_folder"

# Create vis folder if it does not exist
vis_folder="$target_folder/vis"
mkdir -p "$vis_folder"

# Create debug_log.txt file if it does not exist
debug_log_file="$target_folder/debug_log.txt"
touch "$debug_log_file"

# COPY the JSON file to the target folder
cp "$JSON_FILE" "$target_folder"
# Get the "common" name of the JSON file e.g. json {"common": "../common.json"}
common_name=$(jq -r '.common' "$JSON_FILE")
if [ "$common_name" != "null" ]; then
    # If "common" field exists, copy the referenced file to the target folder
    common_path=$(dirname "$JSON_FILE")/"$common_name"
    cp "$common_path" "$target_folder"
fi

"$BIN_FILE"  \
--json "$JSON_FILE" \
-o "$vis_folder" \
--mat_dir "$target_folder" \
--max_threads 16 \
> "$debug_log_file" 2>&1

# gdb --args "$BIN_FILE"  \
# --json "$JSON_FILE" \
# -o "$vis_folder" \
# --mat_dir "$target_folder" \
# --max_threads 16 
# > "$debug_log_file" 2>&1
