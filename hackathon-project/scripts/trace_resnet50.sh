#!/bin/bash
# script to trace resnet50 inference with valgrind

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TRACES_DIR="$SCRIPT_DIR/../traces"
RESNET_SCRIPT="$SCRIPT_DIR/resnet50_inference.py"

mkdir -p "$TRACES_DIR"

echo "--------------------------------------------------------------"
echo "tracing resnet50 with valgrind"
echo "this will take awhile"
echo "output: $TRACES_DIR/resnet50_cpu.stl"
echo "--------------------------------------------------------------"

cd "$SCRIPT_DIR"
valgrind --tool=lackey --trace-mem=yes --log-file="$TRACES_DIR/resnet50_cpu_raw.txt" \
    python3 "$RESNET_SCRIPT" cpu 1

echo ""
echo "converting trace to dramsys format"

python3 << 'PYEOF'
import re
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else "../traces/resnet50_cpu_raw.txt"
output_file = sys.argv[2] if len(sys.argv) > 2 else "../traces/resnet50_cpu.stl"

print(f"reading from: {input_file}")
print(f"writing to: {output_file}")

timestamp = 0
count = 0
max_lines = 100000

with open(input_file, 'r') as fin, open(output_file, 'w') as fout:
    for line in fin:
        if count >= max_lines:
            break

        match = re.match(r'^\s+([LSM])\s+([0-9a-f]+),(\d+)', line)
        if match:
            op_type = match.group(1)
            address = int(match.group(2), 16)

            if op_type in ['L', 'M']:
                fout.write(f"{timestamp} read {address}\n")
                timestamp += 10
                count += 1

            if op_type in ['S', 'M']:
                fout.write(f"{timestamp} write {address}\n")
                timestamp += 10
                count += 1

print(f"converted {count} memory operations")
print("conversion complete")
PYEOF

echo ""
echo "--------------------------------------------------------------"
echo "trace generation complete"
echo "trace file: $TRACES_DIR/resnet50_cpu.stl"
echo "--------------------------------------------------------------"
