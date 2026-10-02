#!/usr/bin/env python3
"""
Usage-Based AI FP&A Model (Python companion to the spreadsheet)

Implements the Base Model described in:
  Chopra, A. (2026). Financial Planning for Agentic & AI Systems: Managing
  Volatility in the Age of Autonomy. California Management Review Insights.
  https://cmr.berkeley.edu/2026/02/financial-planning-for-agentic-ai-systems-managing-volatility-in-the-age-of-autonomy/

Logic (monthly, 36 months):
  Usage        = Customers x Interactions per customer x Tokens per interaction
  Revenue      = On-demand tokens x Price
                 + Prepaid tokens x Price x (1 - Prepaid discount)
                 + Customers x Subscription fee
  LLM cost     = Tokens x Provider cost x (1 - Efficiency gain)
  Cloud cost   = Interactions/1000 x (Compute + Storage + Network rate) x (1 - Cloud discount)
  Other cost   = Revenue x Other cost of revenue %
  Gross margin = Revenue - LLM cost - Cloud cost - Other cost

All example numbers in inputs_template.json are synthetic and illustrative.
Requires: Python 3.9+, numpy, pandas.   License: MIT.

Usage:
  python agentic_ai_fpa_model.py --config ../inputs_template.json --out results
  python agentic_ai_fpa_model.py --config ../inputs_template.json --out results --monte-carlo 5000
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

HORIZON = 36  # months; the spreadsheet uses the same horizon
SCENARIOS = ["low", "base", "high"]
LEVERS = [
    "monthly_customer_growth",
    "monthly_interaction_growth",
    "annual_llm_cost_decline",
    "annual_cloud_cost_decline",
    "efficiency_gain",
]


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def simulate(cfg, levers):
    """Core monthly model.

    Each lever may be a float, or an array of shape (n, 1), so the same code
    serves single scenarios and Monte Carlo runs. Output arrays have shape
    (HORIZON,) for a single scenario or (n, HORIZON) for n runs."""
    u, p, c = cfg["usage"], cfg["pricing"], cfg["cloud_cost"]
    m = np.arange(1, HORIZON + 1)  # month index 1..36

    g = np.asarray(levers["monthly_customer_growth"], dtype=float)
    gi = np.asarray(levers["monthly_interaction_growth"], dtype=float)
    dl = np.asarray(levers["annual_llm_cost_decline"], dtype=float)
    dc = np.asarray(levers["annual_cloud_cost_decline"], dtype=float)
    eff = np.asarray(levers["efficiency_gain"], dtype=float)

    # Usage
    customers = u["starting_customers"] * (1 + g) ** (m - 1)
    ipc = u["interactions_per_customer_per_month"] * (1 + gi) ** (m - 1)
    interactions = customers * ipc
    tokens_k = interactions * u["tokens_per_interaction"] / 1000.0

    # Revenue
    ondemand_k = tokens_k * (1 - p["prepaid_share"])
    prepaid_k = tokens_k * p["prepaid_share"]
    rev_ondemand = ondemand_k * p["price_per_1k_tokens"]
    rev_prepaid = prepaid_k * p["price_per_1k_tokens"] * (1 - p["prepaid_discount"])
    rev_sub = customers * p["subscription_fee_per_customer_per_month"]
    revenue = rev_ondemand + rev_prepaid + rev_sub

    # Cost
    llm_unit = cfg["llm_cost"]["provider_cost_per_1k_tokens"] * (1 - dl) ** ((m - 1) / 12.0)
    llm_cost = tokens_k * llm_unit * (1 - eff)

    cloud_factor = (1 - dc) ** ((m - 1) / 12.0) * (1 - c["discount"])
    compute = interactions / 1000.0 * c["compute_per_1k_interactions"] * cloud_factor
    storage = interactions / 1000.0 * c["storage_per_1k_interactions"] * cloud_factor
    network = interactions / 1000.0 * c["network_per_1k_interactions"] * cloud_factor
    cloud_cost = compute + storage + network

    other = revenue * cfg["other"]["other_cost_of_revenue_pct"]
    total_cost = llm_cost + cloud_cost + other

    # Margin
    gm = revenue - total_cost
    cum_gm = np.cumsum(gm, axis=-1)
    net_position = cum_gm - cfg["investment"]["upfront_investment"]

    shape = gm.shape
    return {
        "month": np.broadcast_to(m, shape),
        "customers": np.broadcast_to(customers, shape),
        "interactions_per_customer": np.broadcast_to(ipc, shape),
        "interactions": np.broadcast_to(interactions, shape),
        "tokens_k": np.broadcast_to(tokens_k, shape),
        "revenue": revenue,
        "llm_cost": llm_cost,
        "compute_cost": compute,
        "storage_cost": storage,
        "network_cost": network,
        "cloud_cost": cloud_cost,
        "other_cost": other,
        "total_cost": total_cost,
        "gross_margin": gm,
        "cum_gross_margin": cum_gm,
        "net_position": net_position,
    }


def risk_factor(cfg):
    """Combined risk factor = (1 - technical) x (1 - data readiness) x (1 - adoption)."""
    h = cfg["investment"]["risk_haircuts"]
    return (1 - h["technical"]) * (1 - h["data_readiness"]) * (1 - h["adoption"])


def roi_pair(cum_gm, cfg):
    """Return (standard ROI ceiling, risk-adjusted ROI floor). Input may be an array.
    Net gain = cumulative gross margin; investment = upfront investment."""
    inv = cfg["investment"]["upfront_investment"]
    if inv == 0:
        return np.nan, np.nan
    ceiling = (cum_gm - inv) / inv
    floor = (cum_gm * risk_factor(cfg) - inv) / inv
    return ceiling, floor


def scenario_frame(cfg, name):
    res = simulate(cfg, cfg["scenarios"][name])
    df = pd.DataFrame({k: np.asarray(v).reshape(-1) for k, v in res.items()})
    df.insert(0, "scenario", name)
    df["gross_margin_pct"] = np.where(df["revenue"] == 0, 0.0, df["gross_margin"] / df["revenue"])
    return df


def summarize(cfg, frames):
    """Annual P&L by scenario and the ROI corridor table."""
    rows = []
    corridor = []
    for name, df in frames.items():
        for yr in (1, 2, 3):
            part = df[(df["month"] > 12 * (yr - 1)) & (df["month"] <= 12 * yr)]
            rev = part["revenue"].sum()
            rows.append({
                "scenario": name,
                "year": yr,
                "revenue": rev,
                "total_cost": part["total_cost"].sum(),
                "gross_margin": part["gross_margin"].sum(),
                "gross_margin_pct": part["gross_margin"].sum() / rev if rev else 0.0,
            })
        cum = df["cum_gross_margin"].iloc[-1]
        ceiling, floor = roi_pair(cum, cfg)
        be = df.loc[df["net_position"] >= 0, "month"]
        corridor.append({
            "scenario": name,
            "cum_gross_margin_36m": cum,
            "roi_ceiling_standard": ceiling,
            "roi_floor_risk_adjusted": floor,
            "payback_month": int(be.iloc[0]) if len(be) else None,
            "trough_net_position": df["net_position"].min(),
            "trough_month": int(df.loc[df["net_position"].idxmin(), "month"]),
        })
    return pd.DataFrame(rows), pd.DataFrame(corridor)


def realized_vs_plan(cfg, base_df):
    """Production stage: compare realized ROI to the Base plan at the same month."""
    a = cfg.get("actuals", {})
    n = int(a.get("months_of_actuals", 0) or 0)
    inv_a = a.get("actual_investment_to_date", 0) or 0
    gm_a = a.get("actual_cumulative_gross_margin_to_date", 0) or 0
    if n < 1 or n > HORIZON or inv_a == 0:
        return None
    inv_plan = cfg["investment"]["upfront_investment"]
    plan_cum = base_df["cum_gross_margin"].iloc[n - 1]
    return {
        "months_of_actuals": n,
        "realized_roi_to_date": float((gm_a - inv_a) / inv_a),
        "plan_roi_same_month_base": float((plan_cum - inv_plan) / inv_plan) if inv_plan else float("nan"),
    }


def monte_carlo(cfg, n_runs=5000, seed=42):
    """Sample each scenario lever from a triangular(low, base, high) distribution,
    run the model, and report percentiles. Illustrative: widen or narrow the
    Low/High values in the config to reflect your own uncertainty."""
    rng = np.random.default_rng(seed)
    s = cfg["scenarios"]
    levers = {}
    for k in LEVERS:
        lo, mode, hi = s["low"][k], s["base"][k], s["high"][k]
        a, b = min(lo, hi), max(lo, hi)
        if a == b:
            levers[k] = np.full((n_runs, 1), a)
        else:
            levers[k] = rng.triangular(a, min(max(mode, a), b), b, size=(n_runs, 1))
    res = simulate(cfg, levers)
    cum = res["cum_gross_margin"][:, -1]
    y3_gm_pct = res["gross_margin"][:, 24:].sum(axis=1) / res["revenue"][:, 24:].sum(axis=1)
    ceiling, floor = roi_pair(cum, cfg)
    out = []
    for label, arr in [
        ("Year 3 gross margin %", y3_gm_pct),
        ("36M cumulative gross margin ($)", cum),
        ("ROI, standard (ceiling)", ceiling),
        ("ROI, risk-adjusted (floor)", floor),
    ]:
        arr = np.asarray(arr, dtype=float)
        out.append({
            "metric": label,
            "p10": np.nanpercentile(arr, 10),
            "p50": np.nanpercentile(arr, 50),
            "p90": np.nanpercentile(arr, 90),
        })
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser(description="Usage-based AI FP&A model")
    ap.add_argument("--config", required=True, help="Path to inputs JSON")
    ap.add_argument("--out", default="results", help="Output folder for CSV files")
    ap.add_argument("--monte-carlo", type=int, default=0, help="Number of simulation runs (0 = skip)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for Monte Carlo")
    args = ap.parse_args()

    cfg = load_config(args.config)
    os.makedirs(args.out, exist_ok=True)
    frames = {n: scenario_frame(cfg, n) for n in SCENARIOS}
    monthly = pd.concat(frames.values(), ignore_index=True)
    annual, corridor = summarize(cfg, frames)
    monthly.to_csv(os.path.join(args.out, "monthly_results.csv"), index=False)
    annual.to_csv(os.path.join(args.out, "annual_summary.csv"), index=False)
    corridor.to_csv(os.path.join(args.out, "roi_corridor.csv"), index=False)

    pd.options.display.float_format = "{:,.3f}".format
    print("\nAnnual summary ($)\n", annual.to_string(index=False))
    print("\nROI corridor (ceiling = standard ROI, floor = risk-adjusted ROI)\n",
          corridor.to_string(index=False))
    print(f"\nRisk factor applied to the floor: {risk_factor(cfg):.4f}")
    rv = realized_vs_plan(cfg, frames["base"])
    if rv:
        print("\nRealized vs plan (Base):",
              {k: round(v, 4) if isinstance(v, float) else v for k, v in rv.items()})
    if args.monte_carlo > 0:
        mc = monte_carlo(cfg, args.monte_carlo, args.seed)
        mc.to_csv(os.path.join(args.out, "monte_carlo_percentiles.csv"), index=False)
        print(f"\nMonte Carlo ({args.monte_carlo} runs, triangular levers, seed {args.seed})\n",
              mc.to_string(index=False))
    print(f"\nCSV files written to: {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
