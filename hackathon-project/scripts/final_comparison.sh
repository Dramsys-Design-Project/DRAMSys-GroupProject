#!/bin/bash

echo "--------------------------------------------------------------------------"
echo "final comparison: resnet50 baseline vs optimized dram"
echo "--------------------------------------------------------------------------"
echo ""

echo "step 1: running real resnet50 inference..."
cd ~/hackathon-project/scripts
python3 resnet50_inference.py cpu 3 2>&1 | tee ~/hackathon-project/results/resnet50_real_performance.log

echo ""
echo "--------------------------------------------------------------------------"
echo "step 2: testing baseline configuration with synthetic trace"
echo "--------------------------------------------------------------------------"
echo "config: ddr4-2400 + brc + fifo"

cd ~/DRAMSys
./build/bin/DRAMSys configs/ai-baseline-ddr4.json 2>&1 | tee ~/hackathon-project/results/FINAL_baseline.log

echo ""
echo "--------------------------------------------------------------------------"
echo "step 3: testing optimized configuration with synthetic trace"
echo "--------------------------------------------------------------------------"
echo "config: ddr4-2400 + brc + fr-fcfs"

cat > ~/DRAMSys/configs/ai-optimized-best.json << 'OPTEOF'
{
    "simulation": {
        "addressmapping": "addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_brc.json",
        "mcconfig": "mcconfig/fr_fcfs.json",
        "memspec": "memspec/JEDEC_4Gb_DDR4-2400_8bit_A.json",
        "simconfig": "simconfig/example.json",
        "simulationid": "ai-optimized-best",
        "tracesetup": [
            {
                "type": "player",
                "clkMhz": 1000,
                "name": "traces/resnet50_synthetic.stl"
            }
        ]
    }
}
OPTEOF

./build/bin/DRAMSys configs/ai-optimized-best.json 2>&1 | tee ~/hackathon-project/results/FINAL_optimized.log

echo ""
echo "--------------------------------------------------------------------------"
echo "comparison complete"
echo "--------------------------------------------------------------------------"
echo "results saved to:"
echo "  - real resnet50: ~/hackathon-project/results/resnet50_real_performance.log"
echo "  - baseline dram: ~/hackathon-project/results/FINAL_baseline.log"
echo "  - optimized dram: ~/hackathon-project/results/FINAL_optimized.log"
echo ""

echo "extracting performance metrics..."
python3 << 'PYEOF'
import re
import json

def extract_metrics(file_path, config_name):
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        total_time = None
        avg_bw = None

        for line in content.split('\n'):
            if 'Total Time:' in line:
                m = re.search(r'Total Time:\s+(\d+)', line)
                if m:
                    total_time = int(m.group(1))
            if 'AVG BW:' in line and 'IDLE' not in line:
                m = re.search(r'AVG BW:\s+([\d.]+)', line)
                if m:
                    avg_bw = float(m.group(1))

        return {
            'config': config_name,
            'total_time_ps': total_time,
            'bandwidth_gbps': avg_bw
        }
    except Exception as e:
        return {'config': config_name, 'error': str(e)}

baseline = extract_metrics('/root/hackathon-project/results/FINAL_baseline.log', 'baseline (fifo)')
optimized = extract_metrics('/root/hackathon-project/results/FINAL_optimized.log', 'optimized (fr-fcfs)')

print("\n" + "-"*80)
print("performance comparison")
print("-"*80)

if baseline.get('total_time_ps') and optimized.get('total_time_ps'):
    print(f"\nbaseline (ddr4-2400 + fifo):")
    print(f"  total time: {baseline['total_time_ps']:,} ps")
    print(f"  bandwidth: {baseline['bandwidth_gbps']:.2f} gb/s")

    print(f"\noptimized (ddr4-2400 + fr-fcfs):")
    print(f"  total time: {optimized['total_time_ps']:,} ps")
    print(f"  bandwidth: {optimized['bandwidth_gbps']:.2f} gb/s")

    improvement_time = ((baseline['total_time_ps'] - optimized['total_time_ps']) /
                        baseline['total_time_ps']) * 100
    improvement_bw = ((optimized['bandwidth_gbps'] - baseline['bandwidth_gbps']) /
                      baseline['bandwidth_gbps']) * 100

    print(f"\nimprovement:")
    print(f"  time reduction: {improvement_time:.2f}%")
    print(f"  bandwidth increase: {improvement_bw:.2f}%")
    print(f"  speedup: {baseline['total_time_ps'] / optimized['total_time_ps']:.2f}x")

    with open('/root/hackathon-project/results/FINAL_COMPARISON.json', 'w') as f:
        json.dump({
            'baseline': baseline,
            'optimized': optimized,
            'improvements': {
                'time_reduction_percent': improvement_time,
                'bandwidth_increase_percent': improvement_bw,
                'speedup_factor': baseline['total_time_ps'] / optimized['total_time_ps']
            }
        }, f, indent=2)

    print(f"\ncomparison saved to: ~/hackathon-project/results/FINAL_COMPARISON.json")
else:
    print("\nerror extracting metrics")
    print(f"baseline: {baseline}")
    print(f"optimized: {optimized}")

print("-"*80)
PYEOF

echo ""
echo "--------------------------------------------------------------------------"
