#!/usr/bin/env python3
"""
test multiple dram configurations for comparison
simple alternative to full optimization runs
"""

import os
import sys
import json
import subprocess
import re

def run_dramsys_simulation(config_name, memspec, addressmapping, mcconfig, trace_file):
    """run one dramsys simulation"""

    dramsys_path = os.path.expanduser("~/DRAMSys")
    config_dict = {
        "simulation": {
            "addressmapping": addressmapping,
            "mcconfig": mcconfig,
            "memspec": memspec,
            "simconfig": "simconfig/example.json",
            "simulationid": config_name,
            "tracesetup": [{
                "type": "player",
                "clkMhz": 1000,
                "name": trace_file
            }]
        }
    }

    config_file = f"{dramsys_path}/configs/test_{config_name}.json"
    with open(config_file, 'w') as f:
        json.dump(config_dict, f, indent=2)

    print("\n" + "-"*70)
    print(f"testing: {config_name}")
    print(f"  memspec: {memspec}")
    print(f"  address mapping: {addressmapping}")
    print(f"  mc config: {mcconfig}")
    print("-"*70)

    try:
        result = subprocess.run(
            [f"{dramsys_path}/build/bin/DRAMSys", config_file],
            capture_output=True,
            text=True,
            timeout=300
        )

        total_time = None
        avg_bw = None

        for line in result.stdout.split('\n'):
            if 'Total Time:' in line:
                m = re.search(r'Total Time:\s+(\d+)', line)
                if m:
                    total_time = int(m.group(1))
            if 'AVG BW:' in line and 'IDLE' not in line:
                m = re.search(r'AVG BW:\s+([\d.]+)', line)
                if m:
                    avg_bw = float(m.group(1))

        return {
            'config_name': config_name,
            'memspec': memspec,
            'addressmapping': addressmapping,
            'mcconfig': mcconfig,
            'total_time_ps': total_time,
            'avg_bandwidth_gbps': avg_bw,
            'success': total_time is not None
        }

    except Exception as e:
        print(f"error: {e}")
        return {
            'config_name': config_name,
            'success': False,
            'error': str(e)
        }

def main():
    test_configs = [
        {
            'name': 'baseline_ddr4_2400',
            'memspec': 'memspec/JEDEC_4Gb_DDR4-2400_8bit_A.json',
            'addressmapping': 'addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_brc.json',
            'mcconfig': 'mcconfig/fr_fcfs.json'
        },
        {
            'name': 'fast_ddr4_3200',
            'memspec': 'memspec/JEDEC_4Gb_DDR4-3200_8bit_A.json',
            'addressmapping': 'addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_brc.json',
            'mcconfig': 'mcconfig/fr_fcfs.json'
        },
        {
            'name': 'ddr4_2400_fifo',
            'memspec': 'memspec/JEDEC_4Gb_DDR4-2400_8bit_A.json',
            'addressmapping': 'addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_brc.json',
            'mcconfig': 'mcconfig/fifo.json'
        },
        {
            'name': 'lpddr4_fast',
            'memspec': 'memspec/JEDEC_LPDDR4_8Gb_die_x16_3200.json',
            'addressmapping': 'addressmapping/am_lpddr4_8Gbx16_brc.json',
            'mcconfig': 'mcconfig/fr_fcfs.json'
        }
    ]

    trace_file = "traces/resnet50_synthetic.stl"
    results = []

    print("\n" + "-"*70)
    print("dram configuration comparison for ai workload")
    print("-"*70)

    for config in test_configs:
        result = run_dramsys_simulation(
            config['name'],
            config['memspec'],
            config['addressmapping'],
            config['mcconfig'],
            trace_file
        )
        results.append(result)

        if result['success']:
            print(f"  total time: {result['total_time_ps']} ps")
            print(f"  avg bandwidth: {result['avg_bandwidth_gbps']:.2f} gb/s")
        else:
            print("  simulation failed")

    results_file = os.path.expanduser('~/hackathon-project/results/config_comparison.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "-"*70)
    print("results summary")
    print("-"*70)

    successful = [r for r in results if r['success']]
    if successful:
        successful.sort(key=lambda x: x['total_time_ps'])

        print("\nranked by total time (lower is better):")
        for i, r in enumerate(successful, 1):
            print(f"\n{i}. {r['config_name']}")
            print(f"   total time: {r['total_time_ps']:,} ps")
            print(f"   bandwidth: {r['avg_bandwidth_gbps']:.2f} gb/s")
            print(f"   memspec: {r['memspec'].split('/')[-1]}")

        best = successful[0]
        baseline = next((r for r in results if 'baseline' in r['config_name']), None)

        if baseline and baseline['success']:
            improvement = ((baseline['total_time_ps'] - best['total_time_ps']) /
                           baseline['total_time_ps'] * 100)
            print("\n" + "-"*70)
            print(f"best configuration: {best['config_name']}")
            print(f"improvement over baseline: {improvement:.2f}%")
            print("-"*70)

    print(f"\ndetailed results saved to: {results_file}")

if __name__ == "__main__":
    main()
