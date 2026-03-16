#!/bin/bash
NUM_THREADS=16
export MKL_THREADING_LAYER=GNU
export MKL_NUM_THREADS=$NUM_THREADS
export OMP_NUM_THREADS=$NUM_THREADS

MESH_NAME="/u/1/chenyang/benchmark_data/larger_matrix_exp/larger_mesh/dataset_curation/result_10000-250000-every-10000/sphere19K_iel0.0078_new_tet_nv242373.msh"
# extract the number from the mesh name
NV=$(echo "$MESH_NAME" | grep -oP 'nv\K\d+')
BIN_FILE="/u/1/chenyang/LearnPolyFEM/polyfem/build.final_large_matrix/PolyFEM_bin"
JSON_FILE="/u/1/chenyang/benchmark_data/larger_matrix_exp/contact/examples/3D/golf-ball.json"

# Absolute path to target folder
target_folder="/mnt/hdd1/chenyang/benchmark_data/larger_matrix_exp/result_10000-250000-every-10000/$NV"
# Create target folder if it does not exist
mkdir -p "$target_folder"

# Create vis folder if it does not exist
vis_folder="$target_folder/vis"
mkdir -p "$vis_folder"

# Create debug_log.txt file if it does not exist
debug_log_file="$target_folder/debug_log.txt"
touch "$debug_log_file"

# Save modified JSON at original location with renamed name: {original}_{NV}_{mesh_dir_folder}.json
json_dir=$(dirname "$JSON_FILE")
json_base=$(basename "$JSON_FILE" .json)
mesh_dir_folder=$(basename "$(dirname "$MESH_NAME")")
source_json="$json_dir/${json_base}_${NV}_${mesh_dir_folder}.json"
jq --arg mesh "$MESH_NAME" '.geometry[0].mesh = $mesh' "$JSON_FILE" > "$source_json"

# Get the "common" name of the JSON file e.g. json {"common": "../common.json"}
common_name=$(jq -r '.common' "$JSON_FILE")
if [ "$common_name" != "null" ]; then
    # If "common" field exists, copy the referenced file to the target folder
    common_path="$json_dir/$common_name"
    cp "$common_path" "$target_folder"
fi

# Copy the modified JSON to target folder
cp "$source_json" "$target_folder"

# Skip if step 61 already reached
if [ -f "$target_folder/61_1_A.bin" ] || [ -f "$target_folder/61_1_b.bin" ]; then
    echo "SKIP nv=$NV (step 61 already reached)"
    exit 0
fi

"$BIN_FILE"  \
--json "$source_json" \
-o "$vis_folder" \
--mat_dir "$target_folder" \
--max_threads $NUM_THREADS \
> "$debug_log_file" 2>&1 &
pid=$!

# Poll for step 61 completion
while kill -0 "$pid" 2>/dev/null; do
    if [ -f "$target_folder/61_1_A.bin" ] || [ -f "$target_folder/61_1_b.bin" ]; then
        echo "STOP nv=$NV (step 61 reached, killing process)"
        kill "$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
        # Delete step 61 files
        rm -f "$target_folder"/61_*
        break
    fi
    sleep 5
done

echo "DONE nv=$NV"
