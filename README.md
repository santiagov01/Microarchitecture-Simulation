# Microarchitecture-Simulation
---

## Overview  
This project varies key microarchitectural parameters (e.g. cache sizes, branch predictor type, rob entries etc.) and runs full simulations to evaluate performance and energy metrics. The goal is to identify the best trade-off configuration in terms of a chosen optimization metric.

The workflow is:  
1. Define a set of microarchitecture parameter options.  
2. Launch simulations for each parameter combination.  
3. Collect metrics (IPC, EDP, etc.).  
4. Analyze results to select the best configuration.  

---

## Repository structure  
- `execution/` : Contains scripts to launch simulations and to process the raw output into results.  
- `Gem5_Simulation_Outputs.ipynb` : A notebook showing how simulation outputs are processed and visualised.  

---

## 📂 Results Folder Structure
`results_<DD_MM>_<metric>/
    results/
        <config1>/
        <config2>/`
Example:
`results_28_10_ipc/
    results/
        config_A/
        config_B/
results_30_10_edp/
    results/
        config_C/
        config_D/`
- `<DD_MM>`: Date of simulation (day_month).
-`<metric>`: Optimization metric (ipc or edp).
-`results/`: Contains folders for each configuration’s outputs and metrics.


