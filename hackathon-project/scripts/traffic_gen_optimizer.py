#!/usr/bin/env python3
"""
traffic generator optimizer - workload parameter tuning
tests: clkmhz, numrequests, rwration, addressdistribution
"""
import os, json, subprocess, re, random
from datetime import datetime

class TrafficGenOptimizer:
    def __init__(self):
        self.dramsys_path = os.path.expanduser("~/DRAMSys")
        self.results_dir = os.path.expanduser("~/hackathon-project/results")

        # best hardware from previous optimization
        self.best_hardware = {
            'memspec': "memspec/JEDEC_4Gb_DDR4-2400_8bit_A.json",
            'addressmapping': "addressmapping/am_ddr4_8x4Gbx8_dimm_p1KB_brc.json",
            'mcconfig': "mcconfig/fr_fcfs.json"
        }

        # traffic generator parameters
        self.clk_options = [800, 1000, 1200, 1600, 2000]
        self.num_req_options = [10000, 30000, 50000, 70000]
        self.rw_ratio_options = [0.6, 0.7, 0.8, 0.9, 0.95]
        self.addr_dist_options = ["random", "sequential"]

        self.all_results = []

    def create_individual(self):
        return {
            **self.best_hardware,
            'clkMhz': random.choice(self.clk_options),
            'numRequests': random.choice(self.num_req_options),
            'rwRatio': random.choice(self.rw_ratio_options),
            'addressDistribution': random.choice(self.addr_dist_options),
            'fitness': None
        }

    def evaluate(self, ind, sim_id):
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
                    "name": f"traffic_gen_{sim_id}",
                    "numRequests": ind['numRequests'],
                    "rwRatio": ind['rwRatio'],
                    "addressDistribution": ind['addressDistribution'],
                    "minAddress": 0,
                    "maxAddress": 4294967295
                }]
            }
        }

        cfg_file = f"{self.dramsys_path}/configs/tgen_{sim_id}.json"
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
        return {
            **self.best_hardware,
            'clkMhz': p1['clkMhz'] if random.random() < 0.5 else p2['clkMhz'],
            'numRequests': p1['numRequests'] if random.random() < 0.5 else p2['numRequests'],
            'rwRatio': p1['rwRatio'] if random.random() < 0.5 else p2['rwRatio'],
            'addressDistribution': p1['addressDistribution'] if random.random() < 0.5 else p2['addressDistribution'],
            'fitness': None
        }

    def mutate(self, ind, rate=0.3):
        if random.random() < rate: ind['clkMhz'] = random.choice(self.clk_options)
        if random.random() < rate: ind['numRequests'] = random.choice(self.num_req_options)
        if random.random() < rate: ind['rwRatio'] = random.choice(self.rw_ratio_options)
        if random.random() < rate: ind['addressDistribution'] = random.choice(self.addr_dist_options)

    def optimize(self, pop_size=8, generations=4):
        print("\n" + "-"*80)
        print("traffic generator optimizer - workload parameter tuning")
        print("-"*80)
        print("hardware: ddr4-2400 + brc + fr-fcfs (from previous optimization)")
        print("optimizing: clkmhz, numrequests, rwration, addressdistribution")
        print(f"search space: {len(self.clk_options)} x {len(self.num_req_options)} x {len(self.rw_ratio_options)} x {len(self.addr_dist_options)} = {len(self.clk_options)*len(self.num_req_options)*len(self.rw_ratio_options)*len(self.addr_dist_options)} configs")
        print("-"*80)

        population = [self.create_individual() for _ in range(pop_size)]
        best_ever = None

        for gen in range(generations):
            print("\n" + "-"*80)
            print(f"generation {gen+1}/{generations}")
            print("-"*80)

            for i, ind in enumerate(population):
                if ind['fitness'] is None:
                    sim_id = f"g{gen}i{i}"
                    print(f"[{i+1}/{pop_size}] clk:{ind['clkMhz']}mhz, req:{ind['numRequests']}, rw:{ind['rwRatio']:.2f}, {ind['addressDistribution'][:3]}... ", end='', flush=True)

                    if self.evaluate(ind, sim_id):
                        print(f"ok {ind['fitness']:,}ps, {ind['bandwidth']:.2f}gb/s")
                        self.all_results.append({'gen': gen+1, 'ind': i, **ind})
                    else:
                        print("fail")

            valid = [i for i in population if i['success']]
            if not valid:
                print("no valid configs")
                continue

            valid.sort(key=lambda x: x['fitness'])
            best = valid[0]
            if best_ever is None or best['fitness'] < best_ever['fitness']:
                best_ever = best.copy()

            print(f"\nbest so far: {best_ever['fitness']:,}ps, {best_ever['bandwidth']:.2f}gb/s")
            print(f"params: {best_ever['clkMhz']}mhz, {best_ever['numRequests']}req, rw:{best_ever['rwRatio']}, {best_ever['addressDistribution']}")

            if gen < generations - 1:
                next_gen = valid[:2]
                while len(next_gen) < pop_size:
                    p1 = min(random.sample(valid, min(2, len(valid))), key=lambda x: x['fitness'])
                    p2 = min(random.sample(valid, min(2, len(valid))), key=lambda x: x['fitness'])
                    child = self.crossover(p1, p2)
                    self.mutate(child)
                    next_gen.append(child)
                population = next_gen[:pop_size]

        if best_ever:
            print("\n" + "-"*80)
            print("optimal traffic generator configuration")
            print("-"*80)
            print(f"time: {best_ever['fitness']:,} ps")
            print(f"bandwidth: {best_ever['bandwidth']:.2f} gb/s")
            print("\nworkload parameters:")
            print(f"clkmhz: {best_ever['clkMhz']} mhz")
            print(f"numrequests: {best_ever['numRequests']}")
            print(f"rwration: {best_ever['rwRatio']}")
            print(f"addressdistribution: {best_ever['addressDistribution']}")

            with open(f"{self.results_dir}/traffic_gen_optimization.json", 'w') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'best': best_ever, 'all': self.all_results}, f, indent=2)
            print(f"\nsaved to: {self.results_dir}/traffic_gen_optimization.json")
            return best_ever

if __name__ == "__main__":
    opt = TrafficGenOptimizer()
    opt.optimize(pop_size=8, generations=4)
