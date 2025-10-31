# sim_assignment/sim_runner.py
import subprocess
import re
import logging
from pathlib import Path
from typing import Tuple, Optional
import os
import matplotlib.pyplot as plt

# ---- CONFIG ----
ROOT_SIMULATION = Path.home() / "gem5"
DIR_MCPAT = ROOT_SIMULATION / "mcpat" / "mcpat"  # ejecutable McPAT esperado aquí
SCRIPTS_DIR = ROOT_SIMULATION / "sim_assignment" / "scripts"
WORKLOADS_DIR = ROOT_SIMULATION / "sim_assignment" / "workloads"
GEM5_BIN = ROOT_SIMULATION / "build" / "ARM" / "gem5.fast"

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

def _safe_search(pattern: str, text: str, default: Optional[float] = None) -> Optional[float]:
    m = re.search(pattern, text)
    if not m:
        return default
    try:
        return m.group(1)
    except (ValueError, IndexError):
        return default

all_stats = {}
for sim_id in range(15):
    outdir = Path(f"output_run_{sim_id}")
    outdir.mkdir(exist_ok=True)
    config_file = outdir / "config.json"
    stats_file = outdir / "stats.txt"

    if not stats_file.exists():
        raise FileNotFoundError(f"Archivo stats no encontrado en {stats_file}")

    text = stats_file.read_text()

    stats = {}
    stats["branchPred_btb_mispredict"] =        _safe_search(r"system.cpu.branchPred.btb.mispredict::total\s+([0-9.eE+-]+)", text) or 0.0
    stats["branchPred_total_btb_lookups"] =     _safe_search(r"system.cpu.branchPred.btb.lookups::total\s+([0-9.eE+-]+)", text) or 0.0
    stats["branchPred_btb_hitrate"] =           _safe_search(r"system.cpu.branchPred.BTBHitRatio\s+([0-9.eE+-]+)", text) or 0.0
    # number of demand (read+write) miss ticks (Tick)
    stats["dcache_demandMissLatency_cpudata"] = _safe_search(r"system.cpu.dcache.demandMissLatency::cpu.data\s+([0-9.eE+-]+)", text) or 0.0 
    stats["dcache_demandMissLatency_total"] =   _safe_search(r"system.cpu.dcache.demandMissLatency::total\s+([0-9.eE+-]+)", text) or 0.0
    stats["dcache_demandHits_total"] =          _safe_search(r"system.cpu.dcache.demandHits::total\s+([0-9.eE+-]+)", text) or 0.0
    stats["dcache_demandMisses"] =              _safe_search(r"system.cpu.dcache.demandMisses::total\s+([0-9.eE+-]+)", text) or 0.0
    stats["IntAlu_statFuBusy"] =                _safe_search(r"system.cpu.statFuBusy::IntAlu\s+([0-9.eE+-]+)", text) or 0.0
    stats["cpi"] =                              _safe_search(r"system.cpu.cpi\s+([0-9.eE+-]+)", text) or 0.0
    stats["simTicks"] =                         _safe_search(r"simTicks \s+([0-9.eE+-]+)", text) or 0.0
    stats["l2_cache_demandMissLatency"] =       _safe_search(r"system.cpu.l2cache.demandHits::total \s+([0-9.eE+-]+)", text) or 0.0
    stats["l2_cache_demandMisses"] =            _safe_search(r"system.cpu.l2cache.overallMisses::total \s+([0-9.eE+-]+)", text) or 0.0

    
    all_stats["Stat"+str(sim_id)] = stats
    
    logger.info(f"Stat{sim_id}: {stats}")
import json
# Nombre del archivo
nombre_archivo = "datos.json"

# Guardar el diccionario en el archivo JSON
with open(nombre_archivo, 'w', encoding='utf-8') as f:
    json.dump(all_stats, f, indent=4) # indent=4 para una mejor legibilidad
