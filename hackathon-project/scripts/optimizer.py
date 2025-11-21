#!/usr/bin/env python3
"""
smart dram optimizer using genetic algorithm
automatically finds best dram configuration for ai workloads
"""

import os
import json
import subprocess
import re
import random
from datetime import datetime

class DRAMOptimizer:
    def __init__(self):
        self.dramsys_path = os.path.expanduser("~/DRAMSys")
        self.results_dir = os.path.expanduser("~/hackathon-project/results")

        # available configurations
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

        self.trace_file = "traces/resnet50_synthetic.stl"
        self.population = []
        self.generation = 0
        self.all_results = []

    def create_individual(self):
        return {
            'memspec': random.choice(self.memspecs),
            'addressmapping': random.choice(self.addressmappings),
            'mcconfig': random.choice(self.mcconfigs),
            'fitness': None
        }

    def evaluate_fitness(self, individual, sim_id):
        config_dict = {
            "simulation": {
                "addressmapping": individual['addressmapping'],
                "mcconfig": individual['mcconfig'],
                "memspec": individual['memspec'],
                "simconfig": "simconfig/example.json",
                "simulationid": sim_id,
                "tracesetup": [{
                    "type": "player",
                    "clkMhz": 1000,
                    "name": self.trace_file
                }]
            }
        }

        config_file = f"{self.dramsys_path}/configs/opt_{sim_id}.json"
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)

        try:
            result = subprocess.run(
                [f"{self.dramsys_path}/build/bin/DRAMSys", config_file],
                capture_output=True,
                text=True,
                timeout=120
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

            individual['fitness'] = total_time if total_time else float('inf')
            individual['bandwidth'] = avg_bw if avg_bw else 0
            individual['success'] = total_time is not None

            return individual['success']

        except Exception:
            individual['fitness'] = float('inf')
            individual['bandwidth'] = 0
            individual['success'] = False
            return False

    def crossover(self, parent1, parent2):
        child = {}
        for key in ['memspec', 'addressmapping', 'mcconfig']:
            child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
        child['fitness'] = None
        return child

    def mutate(self, individual, mutation_rate=0.2):
        if random.random() < mutation_rate:
            individual['memspec'] = random.choice(self.memspecs)
        if random.random() < mutation_rate:
            individual['addressmapping'] = random.choice(self.addressmappings)
        if random.random() < mutation_rate:
            individual['mcconfig'] = random.choice(self.mcconfigs)

    def optimize(self, population_size=12, generations=8, elite_size=2):
        print("\n" + "-"*80)
        print("smart dram optimizer - genetic algorithm")
        print("-"*80)
        print(f"population size: {population_size}")
        print(f"generations: {generations}")
        print(f"configuration space: {len(self.memspecs)} x {len(self.addressmappings)} x {len(self.mcconfigs)}")
        print("-"*80)

        print("\ninitializing population...")
        self.population = [self.create_individual() for _ in range(population_size)]

        best_ever = None

        for gen in range(generations):
            self.generation = gen + 1
            print("\n" + "-"*80)
            print(f"generation {self.generation}/{generations}")
            print("-"*80)

            successful = 0
            for i, individual in enumerate(self.population):
                if individual['fitness'] is None:
                    sim_id = f"g{gen}i{i}"
                    print(f"{i+1}/{population_size} ", end='', flush=True)

                    success = self.evaluate_fitness(individual, sim_id)

                    if success:
                        print(f"time: {individual['fitness']:,} ps, bw: {individual['bandwidth']:.2f} gb/s")
                        successful += 1
                        self.all_results.append({
                            'generation': gen + 1,
                            'individual': i,
                            **individual
                        })
                    else:
                        print("fail")

            valid_pop = [ind for ind in self.population if ind['success']]
            if not valid_pop:
                print("no valid configurations in this generation")
                continue

            valid_pop.sort(key=lambda x: x['fitness'])
            best = valid_pop[0]

            if best_ever is None or best['fitness'] < best_ever['fitness']:
                best_ever = best.copy()

            print(f"\nsummary:")
            print(f"  successful: {successful}/{population_size}")
            print(f"  best this generation: {best['fitness']:,} ps ({best['bandwidth']:.2f} gb/s)")
            print(f"  best overall: {best_ever['fitness']:,} ps ({best_ever['bandwidth']:.2f} gb/s)")

            print("\n  best config:")
            print(f"    memory: {best['memspec'].split('/')[-1]}")
            print(f"    mapping: {best['addressmapping'].split('/')[-1]}")
            print(f"    controller: {best['mcconfig'].split('/')[-1]}")

            if gen < generations - 1:
                next_gen = valid_pop[:elite_size]

                while len(next_gen) < population_size:
                    p1 = min(random.sample(valid_pop, min(3, len(valid_pop))), key=lambda x: x['fitness'])
                    p2 = min(random.sample(valid_pop, min(3, len(valid_pop))), key=lambda x: x['fitness'])

                    child = self.crossover(p1, p2)
                    self.mutate(child)
                    next_gen.append(child)

                self.population = next_gen[:population_size]

        print("\n" + "-"*80)
        print("optimization complete")
        print("-"*80)

        if best_ever:
            print("\nbest configuration found:")
            print(f"  total time: {best_ever['fitness']:,} ps")
            print(f"  bandwidth: {best_ever['bandwidth']:.2f} gb/s")
            print(f"  memory spec: {best_ever['memspec']}")
            print(f"  address mapping: {best_ever['addressmapping']}")
            print(f"  mc config: {best_ever['mcconfig']}")

            best_config_file = f"{self.results_dir}/best_config_optimized.json"
            with open(best_config_file, 'w') as f:
                json.dump({
                    "simulation": {
                        "addressmapping": best_ever['addressmapping'],
                        "mcconfig": best_ever['mcconfig'],
                        "memspec": best_ever['memspec'],
                        "simconfig": "simconfig/example.json",
                        "simulationid": "optimized_best",
                        "tracesetup": [{
                            "type": "player",
                            "clkMhz": 1000,
                            "name": "traces/replace_with_real_trace.stl"
                        }]
                    }
                }, f, indent=2)

            print(f"\nsaved best config to: {best_config_file}")

            results_file = f"{self.results_dir}/optimization_full_results.json"
            with open(results_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'best_configuration': best_ever,
                    'all_generations': self.all_results,
                    'summary': {
                        'total_configurations_tested': len(self.all_results),
                        'generations': generations,
                        'population_size': population_size
                    }
                }, f, indent=2)

            print(f"saved full results to: {results_file}")

            return best_ever

        print("no valid configurations found")
        return None

if __name__ == "__main__":
    optimizer = DRAMOptimizer()
    best = optimizer.optimize(population_size=10, generations=6)
