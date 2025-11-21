#!/usr/bin/env python3
"""
generate synthetic ai workload traces that simulate resnet50 memory access patterns
simplified alternative to full tracing
"""

import random
import sys

def generate_ai_workload_trace(output_file, num_operations=50000):
    """
    generate synthetic ai inference-style trace:
    - sequential reads for weights/features (70%)
    - random reads for activations (20%)
    - writes for output layers (10%)

    format: timestamp:\tread/write\taddress
    """

    print("generating synthetic ai workload trace")
    print(f"operations: {num_operations}")
    print(f"output: {output_file}")

    timestamp = 0
    base_addr = 0x100000000  # 4gb base

    # memory regions
    weight_base = base_addr
    weight_size = 100 * 1024 * 1024

    activation_base = weight_base + weight_size
    activation_size = 200 * 1024 * 1024

    output_base = activation_base + activation_size
    output_size = 50 * 1024 * 1024

    with open(output_file, 'w') as f:
        for i in range(num_operations):
            op_type = random.random()

            if op_type < 0.70:  # sequential weight reads
                addr = weight_base + (i * 64) % weight_size
                f.write(f"{timestamp}:\tread\t0x{addr:x}\n")
                timestamp += 5

            elif op_type < 0.90:  # random activation reads
                addr = activation_base + random.randint(0, activation_size // 64) * 64
                f.write(f"{timestamp}:\tread\t0x{addr:x}\n")
                timestamp += 10

            else:  # output writes
                addr = output_base + random.randint(0, output_size // 64) * 64
                f.write(f"{timestamp}:\twrite\t0x{addr:x}\n")
                timestamp += 15

            if (i + 1) % 10000 == 0:
                print(f"  progress: {i+1}/{num_operations}")

    print("trace generation complete")
    print(f"total cycles: {timestamp}")
    print(f"file: {output_file}")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "../traces/resnet50_synthetic.stl"
    num_ops = int(sys.argv[2]) if len(sys.argv) > 2 else 50000

    generate_ai_workload_trace(output, num_ops)
