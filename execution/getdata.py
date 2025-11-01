# sim_assignment/sim_runner.py
import subprocess
import re
import logging
import os
from typing import Tuple, Optional
import os
import json
import pandas as pd

def _safe_search(pattern: str, text: str, default: Optional[float] = None) -> Optional[float]:
    m = re.search(pattern, text)
    if not m:
        return default
    try:
        return m.group(1)
    except (ValueError, IndexError):
        return default

def extract_simulation_data(path_root: str, csv_path:str) -> dict:
    all_stats = {}
    #listar todos los directorios de acuerdo a path_root
    directories = os.listdir(path_root)
    df = pd.read_csv(csv_path)
    sim_id = 0
    for dir_name in directories:
        stats_file = os.path.join(path_root, dir_name, "stats.txt")

        if not os.path.exists(stats_file):
            raise FileNotFoundError(f"Archivo stats no encontrado en {stats_file}")

        with open(stats_file, 'r') as f:
            text = f.read()

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
        energy = df.loc[sim_id, "energy"]
        edp = df.loc[sim_id, "edp"]
        stats["energy"] = energy
        stats["edp"] = edp
        
        all_stats["Stat"+str(sim_id)] = stats
        sim_id += 1
        

    return all_stats
