import os, re, random, subprocess, csv

# --- Espacios de parámetros ---
params_space = {
    "l1d_size": ["32kB", "64kB", "128kB"],
    "l1d_assoc": [2, 4, 8],
    "l2_size": ["256kB", "512kB", "1MB"],
    "bp_type": [1, 2, 3, 4, 5, 6, 7, 8, 9]
}

# --- Contador global de simulaciones ---
count_output_file = 0

# --- Ejecutar McPAT y calcular energía/EDP ---
def run_mcpat(stats_file, config_file, cpi):
    try:
        cmd = f"./mcpat -infile {config_file} -print_level 1 -statfile {stats_file}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout

        # Extraer valores del archivo de salida
        leak = float(re.search(r"Total Leakage = ([0-9.eE+-]+)", output).group(1))
        dyn = float(re.search(r"Runtime Dynamic = ([0-9.eE+-]+)", output).group(1))
        energy = (leak + dyn) * cpi
        edp = energy * cpi
        return energy, edp
    except Exception as e:
        print("Error ejecutando McPAT:", e)
        return None, None

# --- Ejecutar simulación y extraer métricas ---
def run_simulation(params, sim_id):
    outdir = f"output_run_{sim_id}"
    os.makedirs(outdir, exist_ok=True)  # crea carpeta única por simulación
    stats_file = f"{outdir}/stats.txt"
    config_file = f"{outdir}/config.xml"

    # -- Root folder of simulator --
    ROOT_SIMULATION = "$HOME/gem5"
    # -- Scripts and Workload folder --
    ROOT_SCRIPTS = f"{ROOT_SIMULATION}/sim_assignment/scripts"    
    WKLOAD_DIR = f"{ROOT_SIMULATION}/sim_assignment/workloads"
    
    # -- Binary and Input files --
    BIN_FILE = f"{WKLOAD_DIR}/jpeg2k_dec/jpg2k_dec"
    INPUT_FILE = f"{WKLOAD_DIR}/jpeg2k_dec/jpg2kdec_testfile.j2k"


    cmd = f"{ROOT_SIMULATION}/build/ARM/gem5.fast --outdir={outdir} {ROOT_SCRIPTS}/CortexA76_scripts_gem5/CortexA76.py " \
          f"--stats-file={stats_file} " \
          f"--l1d_size={params['l1d_size']} --l1d_assoc={params['l1d_assoc']} " \
          f"--l2_size={params['l2_size']} --bp-type={params['bp_type']} " \
          f"--dump-config={config_file} " \
          f"-c {BIN_FILE} -o \"-i {INPUT_FILE} -o image.pgm\""

    print(f"Ejecutando simulación {sim_id}...")
    subprocess.run(cmd, shell=True)

    # Leer archivo de estadísticas
    with open(stats_file) as f:
        data = f.read()

    stats = {}
    stats["ipc"] = float(re.search(r"system.cpu.ipc\s+([0-9.eE+-]+)", data).group(1))
    stats["cpi"] = float(re.search(r"system.cpu.cpi\s+([0-9.eE+-]+)", data).group(1))
    stats["l1d_miss_rate"] = float(re.search(r"system.cpu.dcache.overall_miss_rate::total\s+([0-9.eE+-]+)", data).group(1))
    stats["l1i_miss_rate"] = float(re.search(r"system.cpu.icache.overall_miss_rate::total\s+([0-9.eE+-]+)", data).group(1))
    stats["branch_mispred_rate"] = float(re.search(r"system.cpu.branchPred.mispredictions\s+([0-9.eE+-]+)", data).group(1)) / \
                                   float(re.search(r"system.cpu.branchPred.lookups\s+([0-9.eE+-]+)", data).group(1))

    # Ejecutar McPAT
    energy, edp = run_mcpat(stats_file, config_file, stats["cpi"])
    stats["energy"] = energy
    stats["edp"] = edp
    return stats

# --- Inicialización ---
population = [{k: random.choice(v) for k, v in params_space.items()} for _ in range(5)]
all_results = []

for generation in range(3):  # 3 generaciones
    print(f"\n=== GENERACIÓN {generation} ===")
    results = []

    # Evaluar cada individuo
    for individual in population:
        global count_output_file
        stats = run_simulation(individual, count_output_file)
        count_output_file += 1
        fitness = stats["ipc"] / stats["cpi"]  # métrica base de rendimiento
        individual.update(stats)
        individual["fitness"] = fitness
        results.append(individual)
        all_results.append(individual)

    # Selección: los 2 mejores
    results.sort(key=lambda x: x["fitness"], reverse=True)
    best = results[:2]
    print("Mejores de esta generación:", [b["fitness"] for b in best])

    # --- Cruce (combinación) y mutación ---
    new_population = []
    for _ in range(len(population)):
        # Cruzar 2 padres aleatorios del top 2
        parent1, parent2 = random.sample(best, 2)
        child = {}
        for key in params_space.keys():
            # Combina genes de ambos padres
            child[key] = random.choice([parent1[key], parent2[key]])
        # Mutación (10% de probabilidad)
        if random.random() < 0.1:
            p = random.choice(list(params_space.keys()))
            child[p] = random.choice(params_space[p])
        new_population.append(child)

    population = new_population
