# sim_assignment/sim_runner.py
import subprocess
import re
import random
import logging
import csv
from pathlib import Path
from typing import Dict, Tuple, Optional
import os

# ---- CONFIG ----
ROOT_SIMULATION = Path.home() / "gem5"
DIR_MCPAT = ROOT_SIMULATION / "mcpat" / "mcpat"  # ejecutable McPAT esperado aquí
SCRIPTS_DIR = ROOT_SIMULATION / "sim_assignment" / "scripts"
WORKLOADS_DIR = ROOT_SIMULATION / "sim_assignment" / "workloads"
GEM5_BIN = ROOT_SIMULATION / "build" / "ARM" / "gem5.fast"

# Espacio de parámetros
PARAMS_SPACE = {
    "l1d_size": ["32kB", "64kB", "128kB"],
    "l1d_assoc": [2, 4, 8],
    "l2_size": ["256kB", "512kB", "1MB"],
    "bp_type": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "rob_entries": [192, 256],
    "num_fu_intALU" : [2, 4]
}

# Logging
#logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
#save logging file


FILENAME = os.path.basename(__file__)[:-3]


def setup_logger(name: str) -> logging.Logger:
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler(f"{name}.log")
        ]
    )
    logger = logging.getLogger(name)
    return logger


logger = setup_logger(FILENAME)
# ----------------- Helpers -----------------
def _safe_search_float(pattern: str, text: str, default: Optional[float] = None) -> Optional[float]:
    m = re.search(pattern, text)
    if not m:
        return default
    try:
        return float(m.group(1))
    except (ValueError, IndexError):
        return default


# ----------------- McPAT functions -----------------
def build_mcpat_config(stats_file: Path, config_file: Path) -> Path:
    """
    Invoca el script gem5toMcPAT para generar config.xml en el cwd actual.
    Devuelve la ruta al config.xml generado.
    """
    mcpat_script_dir = SCRIPTS_DIR / "McPAT"
    script = mcpat_script_dir / "gem5toMcPAT_cortexA76.py"
    template_xml = mcpat_script_dir / "ARM_A76_2.1GHz.xml"

    if not script.exists():
        raise FileNotFoundError(f"Script gem5toMcPAT no encontrado: {script}")
    if not template_xml.exists():
        raise FileNotFoundError(f"Plantilla XML no encontrada: {template_xml}")

    cmd = [
        "python3",
        str(script),
        str(stats_file),
        str(config_file),
        str(template_xml)
    ]
    logger.info("Construyendo config.xml con gem5toMcPAT...")
    subprocess.run(cmd, check=True)
    generated = Path("config.xml")
    if not generated.exists():
        raise FileNotFoundError("No se generó config.xml después de ejecutar gem5toMcPAT.")
    return generated


def run_mcpat(config_xml: Path, outdir: Path, cpi: float) -> Tuple[Optional[float], Optional[float]]:
    """
    Ejecuta McPAT sobre config.xml y extrae leakage/runtime dynamic -> calcula energy, edp.
    Devuelve (energy, edp) o (None, None) en caso de error.
    """
    # copiar el xml al outdir para conservar registro
    outdir.mkdir(parents=True, exist_ok=True)
    target_xml = outdir / "config.xml"
    target_xml.write_bytes(config_xml.read_bytes())

    mcpat_exec = DIR_MCPAT
    if not mcpat_exec.exists():
        raise FileNotFoundError(f"McPAT ejecutable no encontrado en {mcpat_exec}")

    cmd = [str(mcpat_exec), "-infile", str(target_xml), "-print_level", "1"]
    logger.info(f"Ejecutando McPAT: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        output = result.stdout
        leak = _safe_search_float(r"Total Leakage = ([0-9.eE+-]+)", output)
        dyn = _safe_search_float(r"Runtime Dynamic = ([0-9.eE+-]+)", output)
        if leak is None or dyn is None:
            logger.warning("No se pudieron extraer valores de McPAT (leak/dyn).")
            return None, None
        logger.info(f"Energía dinámica: {dyn}, Energía de fuga: {leak}")
        energy = (leak + dyn) * cpi
        edp = energy * cpi
        return energy, edp
    except subprocess.CalledProcessError as e:
        logger.error("McPAT falló: " + e.stderr)
        return None, None


# ----------------- gem5 simulation -----------------
def run_simulation(params: Dict, sim_id: int) -> Dict:
    """
    Ejecuta una simulación de gem5 con parámetros dados.
    Devuelve un dict con métricas (ipc, cpi, miss rates, energy, edp, ...)
    """
    outdir = Path(f"output_run_{sim_id}")
    outdir.mkdir(exist_ok=True)
    stats_file = outdir / "stats.txt"
    config_file = outdir / "config.json"

    # workload specifics (ajusta si cambia nombre de binario)
    #bin_file = WORKLOADS_DIR / "jpeg2k_dec" / "jpg2k_dec"
    bin_file = WORKLOADS_DIR / "jpeg2k_dec" / "jpg2k_dec"
    input_file = WORKLOADS_DIR / "jpeg2k_dec" / "jpg2kdec_testfile.j2k"

    if not GEM5_BIN.exists():
        raise FileNotFoundError(f"gem5 bin not found: {GEM5_BIN}")
    if not bin_file.exists():
        raise FileNotFoundError(f"Binary not found: {bin_file}")
    if not input_file.exists():
        raise FileNotFoundError(f"Input not found: {input_file}")

    cmd = [
        str(GEM5_BIN),
        f"--outdir={outdir}",
        str(SCRIPTS_DIR / "CortexA76_scripts_gem5" / "CortexA76.py"),
        f"--l1d_size={params['l1d_size']}",
        f"--l1d_assoc={params['l1d_assoc']}",
        f"--l2_size={params['l2_size']}",
        f"--branch_predictor_type={params['bp_type']}",
        f"--rob_entries={params['rob_entries']}",
        f"--num_fu_intALU={params['num_fu_intALU']}",
        f"-c {bin_file} -o \"-i {input_file} -o image.pgm\""
    ]

    logger.info(f"[SIM {sim_id}] Ejecutando gem5...")
    subprocess.run(" ".join(cmd), shell=True, check=True)

    if not stats_file.exists():
        raise FileNotFoundError(f"Archivo stats no encontrado en {stats_file}")

    text = stats_file.read_text()

    stats = {}
    stats["ipc"] = _safe_search_float(r"system.cpu.ipc\s+([0-9.eE+-]+)", text) or 0.0
    stats["cpi"] = _safe_search_float(r"system.cpu.cpi\s+([0-9.eE+-]+)", text) or 0.0
    stats["l1d_miss_rate"] = _safe_search_float(r"system.cpu.dcache.overallMissRate::total\s+([0-9.eE+-]+)", text) or 0.0
    stats["l1i_miss_rate"] = _safe_search_float(r"system.cpu.icache.overallMissRate::total\s+([0-9.eE+-]+)", text) or 0.0

    stats["simSeconds"] = _safe_search_float(r"simSeconds\s+([0-9.eE+-]+)", text) or 0.0
    stats["hostSeconds"] = _safe_search_float(r"hostSeconds\s+([0-9.eE+-]+)", text) or 0.0

    # branch misprediction rate: buscas numerator y denominator
    mispred = _safe_search_float(r"system.cpu.branchPred.mispredicted_0::total\s+([0-9.eE+-]+)", text, 0.0) or 0.0
    lookups = _safe_search_float(r"system.cpu.branchPred.lookups_0::total\s+([0-9.eE+-]+)", text, 1.0) or 1.0
    stats["branch_mispred_rate"] = mispred / lookups if lookups != 0 else 0.0

    # Generar config.xml con McPAT
    try:
        generated_config = build_mcpat_config(stats_file, config_file)
        energy, edp = run_mcpat(generated_config, outdir, stats["cpi"])
    except Exception as e:
        logger.error(f"Error en etapa McPAT: {e}")
        energy, edp = None, None

    stats["energy"] = energy
    stats["edp"] = edp
    return stats


# ----------------- Genetic loop / runner -----------------
def run_genetic(generations: int = 3, pop_size: int = 5, output_csv: str = "results.csv"):
    population = [{k: random.choice(v) for k, v in PARAMS_SPACE.items()} for _ in range(pop_size)]
    all_results = []
    sim_counter = 0

    for gen in range(generations):
        logger.info(f"=== GENERACIÓN {gen} ===")
        results = []
        for individual in population:
            try:
                stats = run_simulation(individual, sim_counter)
            except Exception as e:
                logger.error(f"Simulación {sim_counter} falló: {e}")
                stats = {"ipc": 0.0, "cpi": 0.0, "l1d_miss_rate": None, "l1i_miss_rate": None,
                         "branch_mispred_rate": None,
                         "rob_entries": None, "num_fu_intALU": None, 
                         "simSeconds": None, "hostSeconds": None,
                          "energy": None, "edp": None}
            sim_counter += 1

            #fitness = (stats["ipc"] / stats["cpi"]) if stats["cpi"] not in (0, None) else 0.0
            fitness = stats["ipc"] if stats["ipc"] is not None else 0.0
            #fitness = stats["edp"] if stats["edp"] is not None else 0.0
            combined = {**individual, **stats, "fitness": fitness} 
            results.append(combined)
            all_results.append(combined)

        # Selección top 2
        #results.sort(key=lambda x: x["fitness"], reverse=False)  # minimizar edp
        results.sort(key=lambda x: x["fitness"], reverse=True) # maximizar ipc
        best = results[:2]
        logger.info(f"Mejores de esta generación: {[b['fitness'] for b in best]}")

        # Cruce y mutación
        new_population = []
        for _ in range(len(population)):
            parent1, parent2 = random.sample(best, 2)
            child = {}
            for key in PARAMS_SPACE.keys():
                child[key] = random.choice([parent1[key], parent2[key]])
            if random.random() < 0.1:  # mutación 10%
                p = random.choice(list(PARAMS_SPACE.keys()))
                child[p] = random.choice(PARAMS_SPACE[p])
            new_population.append(child)
        population = new_population

    # Guardar resultados
    if all_results:
        keys = list(all_results[0].keys())
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_results)
        logger.info(f"Resultados guardados en {output_csv}")


if __name__ == "__main__":
    # Ejemplo de ejecución
    run_genetic(generations=3, pop_size=5)
