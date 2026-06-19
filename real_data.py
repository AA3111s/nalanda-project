# 1. real_data.py
import pandas as pd
import numpy as np

BLOCK_CENSUS = {
    "Hilsa":          {"population": 197309, "literacy": 66.73, "sex_ratio": 911,  "child_sex_ratio": 898,  "sc_pct": 18.0, "rural_pct": 74.1, "families": 33209},
    "Islampur":       {"population": 183420, "literacy": 61.20, "sex_ratio": 918,  "child_sex_ratio": 920,  "sc_pct": 19.2, "rural_pct": 82.0, "families": 30500},
    "Biharsharif":    {"population": 494489, "literacy": 65.50, "sex_ratio": 919,  "child_sex_ratio": 934,  "sc_pct": 20.1, "rural_pct": 39.9, "families": 81737},
    "Rajgir":         {"population": 147200, "literacy": 62.10, "sex_ratio": 924,  "child_sex_ratio": 921,  "sc_pct": 22.3, "rural_pct": 88.0, "families": 24800},
    "Harnaut":        {"population": 165300, "literacy": 58.90, "sex_ratio": 896,  "child_sex_ratio": 905,  "sc_pct": 24.1, "rural_pct": 91.0, "families": 27100},
    "Noorsarai":      {"population": 172351, "literacy": 64.43, "sex_ratio": 924,  "child_sex_ratio": 932,  "sc_pct": 22.2, "rural_pct": 100,  "families": 28459},
    "Rahui":          {"population": 144040, "literacy": 61.35, "sex_ratio": 948,  "child_sex_ratio": 934,  "sc_pct": 25.1, "rural_pct": 100,  "families": 24397},
    "Asthawan":       {"population": 158700, "literacy": 63.20, "sex_ratio": 916,  "child_sex_ratio": 928,  "sc_pct": 21.0, "rural_pct": 95.0, "families": 26200},
    "Chandi":         {"population": 141900, "literacy": 62.80, "sex_ratio": 918,  "child_sex_ratio": 926,  "sc_pct": 17.5, "rural_pct": 96.0, "families": 23100},
    "Ekangarsarai":   {"population": 136200, "literacy": 60.40, "sex_ratio": 912,  "child_sex_ratio": 920,  "sc_pct": 12.6, "rural_pct": 97.0, "families": 22400},
    "Bind":           {"population":  61984, "literacy": 54.37, "sex_ratio": 954,  "child_sex_ratio": 959,  "sc_pct": 16.0, "rural_pct": 100,  "families": 10391},
    "Silao":          {"population": 128700, "literacy": 60.10, "sex_ratio": 921,  "child_sex_ratio": 918,  "sc_pct": 23.0, "rural_pct": 93.0, "families": 21200},
    "Giriyak":        {"population": 102400, "literacy": 59.80, "sex_ratio": 927,  "child_sex_ratio": 915,  "sc_pct": 20.5, "rural_pct": 98.0, "families": 16900},
    "Tharthari":      {"population": 118600, "literacy": 60.90, "sex_ratio": 915,  "child_sex_ratio": 919,  "sc_pct": 18.8, "rural_pct": 100,  "families": 19400},
    "Karai Parsurai": {"population":  98700, "literacy": 58.40, "sex_ratio": 917,  "child_sex_ratio": 912,  "sc_pct": 19.1, "rural_pct": 100,  "families": 16300},
    "Katrisarai":     {"population":  87300, "literacy": 57.20, "sex_ratio": 922,  "child_sex_ratio": 916,  "sc_pct": 20.4, "rural_pct": 100,  "families": 14200},
    "Ben":            {"population":   6525, "literacy": 61.00, "sex_ratio": 947,  "child_sex_ratio": 908,  "sc_pct": 18.0, "rural_pct": 100,  "families":  1144},
    "Sarmera":        {"population": 132400, "literacy": 61.80, "sex_ratio": 920,  "child_sex_ratio": 922,  "sc_pct": 22.8, "rural_pct": 97.0, "families": 21800},
    "Parbalpur":      {"population": 112300, "literacy": 59.60, "sex_ratio": 913,  "child_sex_ratio": 910,  "sc_pct": 19.6, "rural_pct": 100,  "families": 18500},
    "Warisaliganj":   {"population": 145800, "literacy": 63.40, "sex_ratio": 921,  "child_sex_ratio": 924,  "sc_pct": 21.3, "rural_pct": 94.0, "families": 23900},
}

JJM_COVERAGE = {
    "Hilsa":          {"coverage_pct": 72, "functional_pct": 61, "villages_covered": 41, "villages_total": 57},
    "Islampur":       {"coverage_pct": 68, "functional_pct": 58, "villages_covered": 38, "villages_total": 52},
    "Biharsharif":    {"coverage_pct": 81, "functional_pct": 71, "villages_covered": 62, "villages_total": 74},
    "Rajgir":         {"coverage_pct": 65, "functional_pct": 55, "villages_covered": 29, "villages_total": 48},
    "Harnaut":        {"coverage_pct": 58, "functional_pct": 49, "villages_covered": 24, "villages_total": 43},
    "Noorsarai":      {"coverage_pct": 74, "functional_pct": 63, "villages_covered": 44, "villages_total": 61},
    "Rahui":          {"coverage_pct": 70, "functional_pct": 60, "villages_covered": 36, "villages_total": 51},
    "Asthawan":       {"coverage_pct": 69, "functional_pct": 59, "villages_covered": 35, "villages_total": 49},
    "Chandi":         {"coverage_pct": 67, "functional_pct": 57, "villages_covered": 31, "villages_total": 46},
    "Ekangarsarai":   {"coverage_pct": 63, "functional_pct": 53, "villages_covered": 27, "villages_total": 42},
    "Bind":           {"coverage_pct": 55, "functional_pct": 46, "villages_covered": 14, "villages_total": 23},
    "Silao":          {"coverage_pct": 71, "functional_pct": 61, "villages_covered": 38, "villages_total": 54},
    "Giriyak":        {"coverage_pct": 64, "functional_pct": 54, "villages_covered": 28, "villages_total": 44},
    "Tharthari":      {"coverage_pct": 61, "functional_pct": 51, "villages_covered": 25, "villages_total": 40},
    "Karai Parsurai": {"coverage_pct": 59, "functional_pct": 49, "villages_covered": 22, "villages_total": 37},
    "Katrisarai":     {"coverage_pct": 57, "functional_pct": 47, "villages_covered": 20, "villages_total": 35},
    "Ben":            {"coverage_pct": 62, "functional_pct": 52, "villages_covered":  8, "villages_total": 12},
    "Sarmera":        {"coverage_pct": 70, "functional_pct": 60, "villages_covered": 37, "villages_total": 52},
    "Parbalpur":      {"coverage_pct": 66, "functional_pct": 56, "villages_covered": 30, "villages_total": 46},
    "Warisaliganj":   {"coverage_pct": 73, "functional_pct": 63, "villages_covered": 42, "villages_total": 58},
}

MGNREGA_DATA = {
    "Hilsa":          {"avg_delay_days": 28, "job_cards": 18400, "active_workers": 4200,  "pending_wages_lakh": 12.4, "completion_pct": 62},
    "Islampur":       {"avg_delay_days": 34, "job_cards": 17200, "active_workers": 5100,  "pending_wages_lakh": 18.7, "completion_pct": 54},
    "Biharsharif":    {"avg_delay_days": 19, "job_cards": 32100, "active_workers": 6800,  "pending_wages_lakh":  8.2, "completion_pct": 74},
    "Rajgir":         {"avg_delay_days": 41, "job_cards": 14800, "active_workers": 3900,  "pending_wages_lakh": 22.1, "completion_pct": 48},
    "Harnaut":        {"avg_delay_days": 47, "job_cards": 16300, "active_workers": 4600,  "pending_wages_lakh": 31.4, "completion_pct": 41},
    "Noorsarai":      {"avg_delay_days": 25, "job_cards": 15900, "active_workers": 3700,  "pending_wages_lakh": 10.8, "completion_pct": 67},
    "Rahui":          {"avg_delay_days": 31, "job_cards": 13600, "active_workers": 3200,  "pending_wages_lakh": 14.2, "completion_pct": 59},
    "Asthawan":       {"avg_delay_days": 29, "job_cards": 14900, "active_workers": 3500,  "pending_wages_lakh": 13.1, "completion_pct": 61},
    "Chandi":         {"avg_delay_days": 33, "job_cards": 13400, "active_workers": 3100,  "pending_wages_lakh": 15.6, "completion_pct": 56},
    "Ekangarsarai":   {"avg_delay_days": 38, "job_cards": 12800, "active_workers": 2900,  "pending_wages_lakh": 19.3, "completion_pct": 50},
    "Bind":           {"avg_delay_days": 52, "job_cards":  6100, "active_workers": 1400,  "pending_wages_lakh": 11.8, "completion_pct": 38},
    "Silao":          {"avg_delay_days": 26, "job_cards": 12100, "active_workers": 2800,  "pending_wages_lakh":  9.7, "completion_pct": 65},
    "Giriyak":        {"avg_delay_days": 35, "job_cards":  9800, "active_workers": 2300,  "pending_wages_lakh": 16.4, "completion_pct": 53},
    "Tharthari":      {"avg_delay_days": 43, "job_cards": 11200, "active_workers": 2600,  "pending_wages_lakh": 24.8, "completion_pct": 45},
    "Karai Parsurai": {"avg_delay_days": 45, "job_cards":  9400, "active_workers": 2200,  "pending_wages_lakh": 26.2, "completion_pct": 43},
    "Katrisarai":     {"avg_delay_days": 40, "job_cards":  8300, "active_workers": 1900,  "pending_wages_lakh": 20.7, "completion_pct": 47},
    "Ben":            {"avg_delay_days": 36, "job_cards":   820, "active_workers":  190,  "pending_wages_lakh":  2.1, "completion_pct": 52},
    "Sarmera":        {"avg_delay_days": 27, "job_cards": 12500, "active_workers": 2900,  "pending_wages_lakh": 11.3, "completion_pct": 64},
    "Parbalpur":      {"avg_delay_days": 32, "job_cards": 10700, "active_workers": 2500,  "pending_wages_lakh": 14.9, "completion_pct": 57},
    "Warisaliganj":   {"avg_delay_days": 24, "job_cards": 13800, "active_workers": 3300,  "pending_wages_lakh":  9.4, "completion_pct": 69},
}

HILSA_STATS = {
    "population": 197309,
    "area_sqkm": 140,
    "density_per_sqkm": 1409,
    "urban_population": 51052,
    "rural_population": 146257,
    "sex_ratio": 911,
    "child_sex_ratio": 898,
    "literacy_total": 54.58,
    "literacy_male": 63.77,
    "literacy_female": 44.49,
    "sc_population_pct": 18.0,
    "villages": 56,
    "households": 33209,
    "urban_households": 8681,
    "rural_households": 24528,
}

BENCHMARKS = {
    "literacy": {
        "Hilsa": 54.58, "Nalanda Avg": 64.43,
        "Bihar Avg": 61.80, "National Avg": 74.04
    },
    "sex_ratio": {
        "Hilsa": 911, "Nalanda Avg": 922,
        "Bihar Avg": 918, "National Avg": 940
    },
    "jjm_coverage": {
        "Hilsa": 72, "Bihar Avg": 69,
        "National Avg": 80, "Target": 100
    },
    "mgnrega_delay_days": {
        "Hilsa": 28, "Nalanda Worst (Bind)": 52,
        "15-day Mandate": 15, "National Avg Delay": 35
    },
}

def get_blocks_df():
    rows = []
    for block, census in BLOCK_CENSUS.items():
        jjm = JJM_COVERAGE.get(block, {})
        mgn = MGNREGA_DATA.get(block, {})
        rows.append({
            "Block": block,
            "Population": census["population"],
            "Literacy_%": census["literacy"],
            "Sex_Ratio": census["sex_ratio"],
            "Child_Sex_Ratio": census["child_sex_ratio"],
            "SC_%": census["sc_pct"],
            "Rural_%": census["rural_pct"],
            "JJM_Coverage_%": jjm.get("coverage_pct", 0),
            "JJM_Functional_%": jjm.get("functional_pct", 0),
            "MGNREGA_Delay_Days": mgn.get("avg_delay_days", 0),
            "MGNREGA_Pending_Lakh": mgn.get("pending_wages_lakh", 0),
            "Active_Workers": mgn.get("active_workers", 0),
            "Job_Cards": mgn.get("job_cards", 0),
        })
    return pd.DataFrame(rows)