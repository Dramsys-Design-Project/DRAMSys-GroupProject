#!/usr/bin/env python3
"""
dram configuration optimizer using genetic algorithm
jlr & uwindsor hackathon
"""

import os
import sys
import json
import subprocess
import random
import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class DRAMConfig:
    """represents a dram configuration"""
    memspec: str
    addressmapping: str
    mcconfig: str
    fitness: float = float('inf')

    def to_dict(self):
        return {
            'memspec': self.memspec,
            'addressmapping': self.addressmappings,
            'mcconfig': self.mcconfig,
            'fitness': self.fitness
        }

class DRAMOptimizer:
    def __init__(self, dramsys_path, trace_file, population_size=20, generations=10):
        self.dramsys_path = dramsys_path
        self.trace_file = trace_file
        self.population_size = population_size
        self.generations = generations
        self.config_base_path = os.path.join(dramsys_path, 'configs')

        # available configurations
        self.memspecs = self._discover_configs('memspec')
        self.addressmappings = self._discover_configs('addressmapping')
        self.mcconfigs = self._discover_configs('mcconfig')

        print("discovered configurations:")
        print(f"  memory specs: {len(self.memspecs)}")
        print(f"  address mappings: {len(self.addressmappings)}")
        print(f"  mc configs: {len(self.mcconfigs)}")

    def _discover_configs(self, config_type):
        """discover available configuration files"""
        path = os.path.join(self.config_base_path, config_type)
        if not os.path.exists(path):
            print(f"warning: {path} doesn't exist")
            return []

        configs = []
        for file in os.listdir(path):
            if file.endswith('.json'):
                configs.append(f"{config_type}/{file}")
        return configs

    def create_random_config(self) -> DRAMConfig:
        """create a random dram configuration"""
        return DRAMConfig(
            memspec=random.choice(self.memspecs),
            addressmapping=random.choice(self.addressmappings),
            mcconfig=random.choice(self.mcconfigs)
        )

    def evaluate_config(self, config: DRAMConfig, simulation_id: str) -> float:
        """evaluate a configuration by running dramsys simulation"""
        config_dict = {
            "simulation": {
                "addressmapping": config.addressmapping,
                "mcconfig": config.mcconfig,
                "memspec": config.memspec,
                "simconfig": "simconfig/example.json",
                "simulationid": simulation_id,
                "tracesetup": [{
                    "type": "player",
                    "clkMhz": 1000,
                    "name": self.trace_file
                }]
            }
        }

        config_file = f"/tmp/dramsys_config_{simulation_id}.json"
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)

        try:
            result = subprocess.run(
                [os.path.join(self.dramsys_path, 'build/bin/DRAMSys'), config_file],
                capture_output=True,
                text=True,
                timeout=300
            )

            for line in result.stdout.split('\n'):
                if 'Total Time:' in line:
                    match = re.search(r'Total Time:\s+(\d+)', line)
                    if match:
                        return int(match.group(1))

            return float('inf')

        except subprocess.TimeoutExpired:
            print(f"  simulation timeout for {simulation_id}")
            return float('inf')
        except Exception as e:
            print(f"  error running simulation: {e}")
            return float('inf')
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)

    def crossover(self, parent1: DRAMConfig, parent2: DRAMConfig) -> Tuple[DRAMConfig, DRAMConfig]:
        """perform crossover between two parents"""
        genes = ['memspec', 'addressmapping', 'mcconfig']
        crossover_point = random.randint(0, len(genes))

        child1_genes = {}
        child2_genes = {}

        for i, gene in enumerate(genes):
            if i < crossover_point:
                child1_genes[gene] = getattr(parent1, gene)
                child2_genes[gene] = getattr(parent2, gene)
            else:
                child1_genes[gene] = getattr(parent2, gene)
                child2_genes[gene] = getattr(parent1, gene)

        return DRAMConfig(**child1_genes), DRAMConfig(**child2_genes)

    def mutate(self, config: DRAMConfig, mutation_rate=0.1):
        """mutate a configuration"""
        if random.random() < mutation_rate:
            config.memspec = random.choice(self.memspecs)
        if random.random() < mutation_rate:
            config.addressmapping = random.choice(self.addressmappings)
        if random.random() < mutation_rate:
            config.mcconfig = random.choice(self.mcconfigs)

    def optimize(self):
        """run genetic algorithm optimization"""
        print("\n" + "-" * 70)
        print("dram configuration optimization: genetic algorithm")
        print("-" * 70)

        population = [self.create_random_config() for _ in range(self.population_size)]
        best_configs = []

        for generation in range(self.generations):
            print(f"\n--- generation {generation + 1}/{self.generations} ---")

            for i, config in enumerate(population):
                sim_id = f"gen{generation}_ind{i}"
                print(f"  evaluating individual {i+1}/{self.population_size}...", end=' ')
                fitness = self.evaluate_config(config, sim_id)
                config.fitness = fitness
                print(f"fitness: {fitness if fitness != float('inf') else 'failed'}")

            population.sort(key=lambda x: x.fitness)

            best = population[0]
            print("\n  best configuration:")
            print(f"    memspec: {best.memspec}")
            print(f"    address mapping: {best.addressmapping}")
            print(f"    mc config: {best.mcconfig}")
            print(f"    total time: {best.fitness} ps")

            best_configs.append(best.to_dict())

            survivors = population[:self.population_size // 2]
            next_generation = survivors.copy()

            while len(next_generation) < self.population_size:
                parent1 = random.choice(survivors)
                parent2 = random.choice(survivors)

                child1, child2 = self.crossover(parent1, parent2)
                self.mutate(child1)
                self.mutate(child2)

                next_generation.extend([child1, child2])

            population = next_generation[:self.population_size]

        print("\n" + "-" * 70)
        print("optimization complete")
        print("-" * 70)

        best = min(best_configs, key=lambda x: x['fitness'])
        print("\nbest configuration found:")
        print(json.dumps(best, indent=2))

        results_file = os.path.expanduser('~/hackathon-project/results/optimization_results.json')
        with open(results_file, 'w') as f:
            json.dump({
                'best_config': best,
                'all_generations': best_configs
            }, f, indent=2)

        print(f"\nresults saved to: {results_file}")

        return best

if __name__ == "__main__":
    dramsys_path = os.path.expanduser("~/DRAMSys")
    trace_file = "traces/resnet50_synthetic.stl"

    optimizer = DRAMOptimizer(
        dramsys_path=dramsys_path,
        trace_file=trace_file,
        population_size=10,
        generations=5
    )

    best_config = optimizer.optimize()
