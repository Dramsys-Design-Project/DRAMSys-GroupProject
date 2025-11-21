#!/bin/bash

echo "------------------------------------------------------------------------"
echo "creating real resnet50 memory trace with valgrind"
echo "may take 10-30 minutes"
echo "------------------------------------------------------------------------"

cd ~/hackathon-project/scripts

echo "running resnet50 under valgrind..."
valgrind --tool=lackey --trace-mem=yes --log-file=/tmp/resnet50_valgrind_raw.txt \
    python3 resnet50_inference.py cpu 1

echo ""
echo "converting trace to dramsys format..."

python3 << 'PYEOF'
import re

print("processing valgrind output...")
timestamp = 0
count = 0
max_ops = 100000  # limit for manageable simulation time

input_file = "/tmp/resnet50_valgrind_raw.txt"
output_file = "/root/DRAMSys/configs/traces/resnet50_real.stl"

with open(input_file, 'r') as fin, open(output_file, 'w') as fout:
    for line in fin:
        if count >= max_ops:
            break

        match = re.match(r'^\s+([LSM])\s+([0-9a-f]+),(\d+)', line)
        if match:
            op_type = match.group(1)
            address = int(match.group(2), 16)

            if op_type in ['L', 'M']:
                fout.write(f"{timestamp}:\tread\t0x{address:x}\n")
                timestamp += 5
                count += 1

            if op_type in ['S', 'M']:
                fout.write(f"{timestamp}:\twrite\t0x{address:x}\n")
                timestamp += 5
                count += 1

        if count % 10000 == 0 and count > 0:
            print(f"  processed {count} operations...")

print(f"\ncreated trace with {count} memory operations")
print(f"total simulated time: {timestamp} cycles")
print(f"output: {output_file}")
PYEOF

echo ""
echo "------------------------------------------------------------------------"
echo "real resnet50 trace created"
echo "location: ~/dramsys/configs/traces/resnet50_real.stl"
echo "------------------------------------------------------------------------"
