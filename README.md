# DRAM Configuration Optimization

This project uses DRAMSys and a Genetic Algorithm to search for optimal an DRAM configurations for AI workloads. Synthetic ResNet50-like traces are generated and evaluated through multiple DRAM simulations to identify the best-performing memory setup.

# Features

Synthetic ResNet50 memory trace generation

Baseline DRAM simulation using DRAMSys

Genetic Algorithm for configuration search

Automated evaluation of memory specs, address mappings, and controller policies

Comparison of multiple configurations

# Quick Start
Generate Synthetic Trace
cd scripts
python3 create_synthetic_ai_trace.py ~/DRAMSys/configs/traces/resnet50_synthetic.stl 50000

file structure:

root folder/
- DRAMSys
- hackathon-project
    

# Run Baseline DRAM Simulation
cd ~/DRAMSys
./build/bin/DRAMSys configs/ai-baseline-ddr4.json

# Run the Optimizer
cd scripts
python3 optimizer.py

# Compare Predefined Configurations
python3 test_multiple_configs.py

# Results

Outputs are stored in:

results/
- optimization_full_results.json
- best_config_optimized.json
- config_comparison.json



#File Structure
scripts/    Trace generator, optimizer, ResNet50 inference test
results/    All simulation and optimization outputs
configs/    DRAMSys configuration files

