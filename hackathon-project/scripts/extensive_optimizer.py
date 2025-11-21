#!/usr/bin/env python3
"""
dram optimizer: full parameter search using evolutionary sampling.
searches both hardware and traffic generator parameters.
"""

import os, json, subprocess, re, random
from datetime import datetime

class ExtensiveOptimizer:
    def __init__(self):
        self.dramsys_path = os.path.expanduser("~/DRAMSys")
        self.results_dir = os.path.expanduser("~/hackathon-project/results")

        # Hardware parameter lists
        self.memspecs = [
            "memspec/JEDEC_4Gb_DDR4-1866_8bit_A.json",
            "memspec/JEDEC_4Gb_DDR4-2400_8bit_A.json",
            "memspec/JEDEC_4Gb_DDR4-2666_8bit_A.json",
            "memspec/JEDEC_8Gb_DDR4-1866_8bit_A.json",
            "memspec/JEDEC_8Gb_DDR4-2400_8bit_A.json",
        ]

        self.addressmappings = [
            "addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_brc.json",
            "addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_rbc.json",
        ]

        self.mcconfigs = [
            "mcconfig/fifo.json",
            "mcconfig/fr_fcfs.json",
        ]

        # Workload parameter lists
        self.clk_options = [800, 1000, 1200, 1600, 2000]
        self.num_req_options = [10000, 30000, 50000, 70000, 100000]
        self.rw_ratio_options = [0.6, 0.7, 0.8, 0.9, 0.95]
        self.addr_dist_options = ["random", "sequential"]

        total_configs = (
                len(self.memspecs)
                * len(self.addressmappings)
                * len(self.mcconfigs)
                * len(self.clk_options)
                * len(self.num_req_options)
                * len(self.rw_ratio_options)
                * len(self.addr_dist_options)
        )

        print("-" * 80)
        print("extensive dram optimization")
        print("-" * 80)
        print(f"search space: {total_configs:,} configurations")
        print("-" * 80)

        self.all_results = []
        self.tested_configs = set()

    def create_individual(self):
        """Random parameter sample."""
        cfg = (
            random.choice(self.memspecs),
            random.choice(self.addressmappings),
            random.choice(self.mcconfigs),
            random.choice(self.clk_options),
            random.choice(self.num_req_options),
            random.choice(self.rw_ratio_options),
            random.choice(self.addr_dist_options)
        )

        while str(cfg) in self.tested_configs:
            cfg = (
                random.choice(self.memspecs),
                random.choice(self.addressmappings),
                random.choice(self.mcconfigs),
                random.choice(self.clk_options),
                random.choice(self.num_req_options),
                random.choice(self.rw_ratio_options),
                random.choice(self.addr_dist_options)
            )

        self.tested_configs.add(str(cfg))

        return {
            'memspec': cfg[0],
            'addressmapping': cfg[1],
            'mcconfig': cfg[2],
            'clkMhz': cfg[3],
            'numRequests': cfg[4],
            'rwRatio': cfg[5],
            'addressDistribution': cfg[6],
            'fitness': None
        }

    def evaluate(self, ind, sim_id):
        """Run DRAMSys and extract timing/bandwidth."""
        config = {
            "simulation": {
                "addressmapping": ind['addressmapping'],
                "mcconfig": ind['mcconfig'],
                "memspec": ind['memspec'],
                "simconfig": "simconfig/example.json",
                "simulationid": sim_id,
                "tracesetup": [{
                    "type": "generator",
                    "clkMhz": ind['clkMhz'],
                    "name": f"ext_{sim_id}",
                    "numRequests": ind['numRequests'],
                    "rwRatio": ind['rwRatio'],
                    "addressDistribution": ind['addressDistribution'],
                    "minAddress": 0,
                    "maxAddress": 4294967295
                }]
            }
        }

        cfg_file = f"{self.dramsys_path}/configs/ext_{sim_id}.json"
        with open(cfg_file, 'w') as f:
            json.dump(config, f, indent=2)

        try:
            result = subprocess.run(
                [f"{self.dramsys_path}/build/bin/DRAMSys", cfg_file],
                capture_output=True, text=True, timeout=120
            )

            total_time, avg_bw = None, None
            for line in result.stdout.split('\n'):
                if 'Total Time:' in line:
                    m = re.search(r'Total Time:\s+(\d+)', line)
                    if m: total_time = int(m.group(1))
                if 'AVG BW:' in line and 'IDLE' not in line:
                    m = re.search(r'AVG BW:\s+([\d.]+)', line)
                    if m: avg_bw = float(m.group(1))

            ind['fitness'] = total_time if total_time else float('inf')
            ind['bandwidth'] = avg_bw if avg_bw else 0
            ind['success'] = total_time is not None
            return ind['success']

        except:
            ind['fitness'], ind['bandwidth'], ind['success'] = float('inf'), 0, False
            return False

    def crossover(self, p1, p2):
        """Uniform crossover."""
        return {
            k: (p1[k] if random.random() < 0.5 else p2[k])
            for k in ['memspec', 'addressmapping', 'mcconfig',
                      'clkMhz', 'numRequests', 'rwRatio', 'addressDistribution']
        } | {'fitness': None}

    def mutate(self, ind, rate=0.25):
        """Mutate fields"""
        if random.random() < rate: ind['memspec'] = random.choice(self.memspecs)
        if random.random() < rate: ind['addressmapping'] = random.choice(self.addressmappings)
        if random.random() < rate: ind['mcconfig'] = random.choice(self.mcconfigs)
        if random.random() < rate: ind['clkMhz'] = random.choice(self.clk_options)
        if random.random() < rate: ind['numRequests'] = random.choice(self.num_req_options)
        if random.random() < rate: ind['rwRatio'] = random.choice(self.rw_ratio_options)
        if random.random() < rate: ind['addressDistribution'] = random.choice(self.addr_dist_options)

    def optimize(self, pop_size=15, generations=8):
        """optimization loop."""

        print(f"population: {pop_size}, generations: {generations}")
        print("-" * 80)

        population = [self.create_individual() for _ in range(pop_size)]
        best_ever = None
        generation_bests = []

        for gen in range(generations):
            print(f"\ngeneration {gen+1}/{generations}")
            successful = 0

            for i, ind in enumerate(population):
                if ind['fitness'] is None:
                    print(f"{i+1}/{pop_size} ", end='', flush=True)
                    sim_id = f"g{gen}i{i}"

                    if self.evaluate(ind, sim_id):
                        print(f"ok   time={ind['fitness']:,}  bw={ind['bandwidth']:.2f}")
                        successful += 1
                        self.all_results.append({'gen': gen+1, **ind})
                    else:
                        print("fail")

            valid = [i for i in population if i['success']]
            if not valid:
                print("no valid samples")
                continue

            valid.sort(key=lambda x: x['fitness'])
            best = valid[0]

            if best_ever is None or best['fitness'] < best_ever['fitness']:
                best_ever = best.copy()

            generation_bests.append(best_ever['fitness'])

            if gen < generations - 1:
                elite = max(2, pop_size // 5)
                next_gen = valid[:elite]

                while len(next_gen) < pop_size:
                    p1 = min(random.sample(valid, min(3, len(valid))), key=lambda x: x['fitness'])
                    p2 = min(random.sample(valid, min(3, len(valid))), key=lambda x: x['fitness'])
                    child = self.crossover(p1, p2)
                    self.mutate(child)
                    next_gen.append(child)

                population = next_gen[:pop_size]

        # Final output
        if best_ever:
            results_file = f"{self.results_dir}/extensive_optimization_FINAL.json"
            with open(results_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'best_configuration': best_ever,
                    'progress': generation_bests,
                    'all_results': self.all_results,
                    'stats': {
                        'total_tested': len(self.all_results),
                        'unique_configs': len(self.tested_configs),
                        'generations': generations,
                        'population_size': pop_size
                    }
                }, f, indent=2)

            print("\noptimization complete")
            print(f"best time: {best_ever['fitness']:,} ps")
            print(f"results saved: {results_file}")

            return best_ever

        print("no valid configuration found")
        return None


if __name__ == "__main__":
    optimizer = ExtensiveOptimizer()
    optimizer.optimize(pop_size=12, generations=6)
