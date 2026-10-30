from schema import IPPAnalysisInput

def _npv(rate: float, values: list) -> float:
    """Calculates Present Value of a series starting at period t=1."""
    return sum(v / ((1.0 + rate) ** (t + 1)) for t, v in enumerate(values))

def _calc_irr(cf: list) -> float:
    """Pure-Python bisection IRR solver for [-cf0, cf1, cf2, ...]."""
    if not cf or cf[0] >= 0 or sum(cf) <= 0:
        return 0.0
    low, high = -0.50, 2.00
    for _ in range(80):
        mid = (low + high) / 2.0
        npv_val = sum(c / ((1.0 + mid) ** t) for t, c in enumerate(cf))
        if npv_val > 0:
            low = mid
        else:
            high = mid
    return round(((low + high) / 2.0) * 100.0, 2)

def _simulate_capital_structure(data: IPPAnalysisInput, tariff_usd_mwh: float) -> dict:
    # 1. Total Installed CAPEX ($ Millions)
    gen_capex_m = (data.capacity_mw * 1000.0 * data.capex_per_kw) / 1e6
    bess_capex_m = (data.bess_capacity_mwh * 1000.0 * data.bess_capex_per_kwh) / 1e6
    total_capex_m = gen_capex_m + bess_capex_m

    # Annual Fixed O&M ($ Millions) - adding BESS O&M allowance if storage is present
    bess_om_m = (data.bess_capacity_mwh * 1000.0 * 5.0) / 1e6
    annual_om_m = ((data.capacity_mw * 1000.0 * data.fixed_om_per_kw_yr) / 1e6) + bess_om_m

    # 2. Multi-Year Generation & CFADS Vectors across P50, P90, and P99
    n_ppa = data.ppa_tenor_years
    n_debt = min(data.debt_tenor_years, n_ppa)
    deg = data.annual_degradation_pct / 100.0
    r_d = data.interest_rate_pct / 100.0

    gen_p50_mwh, cfads_p50_m, cfads_p90_m, cfads_p99_m = [], [], [], []

    for yr in range(1, n_ppa + 1):
        deg_factor = (1.0 - deg) ** (yr - 1)
        mwh_50 = data.capacity_mw * 8760.0 * (data.p50_cf_pct / 100.0) * deg_factor
        mwh_90 = data.capacity_mw * 8760.0 * (data.p90_1yr_cf_pct / 100.0) * deg_factor
        mwh_99 = data.capacity_mw * 8760.0 * (data.p99_1yr_cf_pct / 100.0) * deg_factor

        gen_p50_mwh.append(mwh_50)
        cfads_p50_m.append(max(0.0, (mwh_50 * tariff_usd_mwh / 1e6) - annual_om_m))
        cfads_p90_m.append(max(0.0, (mwh_90 * tariff_usd_mwh / 1e6) - annual_om_m))
        cfads_p99_m.append(max(0.0, (mwh_99 * tariff_usd_mwh / 1e6) - annual_om_m))

    # 3. Bodmer Non-Circular Multi-Criteria Debt Sizing over Debt Horizon
    target_ds_p50 = [cf / data.target_dscr_p50 for cf in cfads_p50_m[:n_debt]]
    target_ds_p90 = [cf / data.target_dscr_p90 for cf in cfads_p90_m[:n_debt]]
    target_ds_p99 = [cf / data.target_dscr_p99 for cf in cfads_p99_m[:n_debt]]

    debt_p50_m = _npv(r_d, target_ds_p50)
    debt_p90_m = _npv(r_d, target_ds_p90)
    debt_p99_m = _npv(r_d, target_ds_p99)
    debt_gearing_m = total_capex_m * (data.max_gearing_pct / 100.0)

    constraints = {
        "P50 Target DSCR": debt_p50_m,
        "1-Yr P90 Target DSCR": debt_p90_m,
        "1-Yr P99 Breakeven": debt_p99_m,
        "Max Gearing Cap": debt_gearing_m
    }
    binding_constraint = min(constraints, key=constraints.get)
    max_debt_m = max(0.0, constraints[binding_constraint])
    sponsor_equity_m = max(0.01, total_capex_m - max_debt_m)

    # 4. Sculpted Debt Service Schedule matched to P90 Cash Flow Profile
    # Since PV(target_ds_p90) = debt_p90_m, scaling target_ds_p90 by (max_debt_m / debt_p90_m)
    # guarantees exact payoff of max_debt_m at interest rate r_d with flat DSCR!
    scale_factor = (max_debt_m / debt_p90_m) if debt_p90_m > 0 else 0.0

    debt_service_m = []
    debt_balance_m = []
    rem_debt = max_debt_m

    for t in range(n_ppa):
        if t < n_debt and rem_debt > 1e-6:
            interest_m = rem_debt * r_d
            sculpted_ds = target_ds_p90[t] * scale_factor
            principal_m = max(0.0, min(rem_debt, sculpted_ds - interest_m))
            actual_ds = interest_m + principal_m
            rem_debt = max(0.0, rem_debt - principal_m)
        else:
            actual_ds = 0.0
        debt_service_m.append(actual_ds)
        debt_balance_m.append(rem_debt)

    # 5. Equity Cash Flow Waterfall & Coverage Ratios
    equity_cf_m = [-sponsor_equity_m] + [cfads_p50_m[t] - debt_service_m[t] for t in range(n_ppa)]
    equity_irr_pct = _calc_irr(equity_cf_m)

    dscr_p90_series = [
        cfads_p90_m[t] / debt_service_m[t] for t in range(n_debt) if debt_service_m[t] > 0
    ]
    dscr_p50_series = [
        cfads_p50_m[t] / debt_service_m[t] for t in range(n_debt) if debt_service_m[t] > 0
    ]
    min_dscr_p90 = min(dscr_p90_series) if dscr_p90_series else 0.0
    min_dscr_p50 = min(dscr_p50_series) if dscr_p50_series else 0.0

    pv_cfads_loan = _npv(r_d, cfads_p50_m[:n_debt])
    pv_cfads_proj = _npv(r_d, cfads_p50_m)
    llcr = (pv_cfads_loan / max_debt_m) if max_debt_m > 0 else 0.0
    plcr = (pv_cfads_proj / max_debt_m) if max_debt_m > 0 else 0.0
    breakeven_cf_drop_pct = max(0.0, ((llcr - 1.0) / llcr) * 100.0) if llcr > 1.0 else 0.0

    return {
        "total_capex_m": total_capex_m,
        "max_debt_m": max_debt_m,
        "sponsor_equity_m": sponsor_equity_m,
        "binding_constraint": binding_constraint,
        "constraints": {k: round(v, 2) for k, v in constraints.items()},
        "equity_irr_pct": equity_irr_pct,
        "min_dscr_p90": min_dscr_p90,
        "min_dscr_p50": min_dscr_p50,
        "llcr": llcr,
        "plcr": plcr,
        "breakeven_cf_drop_pct": breakeven_cf_drop_pct,
        "gen_p50_mwh": gen_p50_mwh,
        "cfads_p50_m": cfads_p50_m,
        "cfads_p90_m": cfads_p90_m,
        "debt_service_m": debt_service_m,
        "debt_balance_m": debt_balance_m,
        "equity_cf_m": equity_cf_m[1:],
        "annual_om_m": annual_om_m
    }

def analyze_ipp_project(data: IPPAnalysisInput) -> dict:
    # Step 1: Run Base Simulation at User's Entered Tariff
    sim = _simulate_capital_structure(data, data.ppa_tariff_usd_mwh)

    # Step 2: Two-Step Institutional Auction Tariff Solver (Finds Minimum Tariff for Target Equity IRR)
    low_t, high_t = 5.0, 250.0
    for _ in range(45):
        mid_t = (low_t + high_t) / 2.0
        test_irr = _simulate_capital_structure(data, mid_t)["equity_irr_pct"]
        if test_irr < data.target_equity_irr_pct:
            low_t = mid_t
        else:
            high_t = mid_t
    min_winning_tariff = round((low_t + high_t) / 2.0, 2)

    # Step 3: Institutional LCOE Calculation (Discounted at Implied WACC)
    gearing = sim["max_debt_m"] / sim["total_capex_m"] if sim["total_capex_m"] > 0 else 0.0
    wacc = (gearing * (data.interest_rate_pct / 100.0)) + ((1.0 - gearing) * (data.target_equity_irr_pct / 100.0))
    pv_costs_m = sim["total_capex_m"] + _npv(wacc, [sim["annual_om_m"]] * data.ppa_tenor_years)
    pv_energy_mwh = _npv(wacc, sim["gen_p50_mwh"])
    lcoe_usd_mwh = round((pv_costs_m * 1e6) / pv_energy_mwh, 2) if pv_energy_mwh > 0 else 0.0

    # Step 4: Fitch Ratings Volume Risk Spread (1 - P90_1yr / P50)
    fitch_spread_pct = round((1.0 - (data.p90_1yr_cf_pct / data.p50_cf_pct)) * 100.0, 2)
    if fitch_spread_pct <= 6.0:
        fitch_vol_rating = "STRONGER (<=6% Spread)"
    elif fitch_spread_pct <= 16.0:
        fitch_vol_rating = "MIDRANGE (6%-16% Spread - BBB Category)"
    else:
        fitch_vol_rating = "WEAKER (>16% Spread)"

    # Step 5: Open Solar Contracts / MENA GSA Termination Buyout Valuation (Year 1 vs. Year 5)
    c_term_m = round(sim["annual_om_m"] * 0.50, 2)  # Termination wind-down costs
    eq_return_m = round(sim["sponsor_equity_m"] * ((1.0 + (data.target_equity_irr_pct / 100.0)) ** 3 - 1.0), 2)
    yr5_idx = min(4, len(sim["debt_balance_m"]) - 1)
    debt_yr1_m = sim["max_debt_m"]
    debt_yr5_m = sim["debt_balance_m"][yr5_idx]

    buyout_schedule = {
        "offtaker_default_yr1_m": round(debt_yr1_m + sim["sponsor_equity_m"] + eq_return_m + c_term_m, 2),
        "offtaker_default_yr5_m": round(debt_yr5_m + sim["sponsor_equity_m"] + eq_return_m + c_term_m, 2),
        "project_default_yr1_m": round(debt_yr1_m + c_term_m, 2),
        "project_default_yr5_m": round(debt_yr5_m + c_term_m, 2),
        "natural_fm_yr1_m": round(debt_yr1_m + c_term_m, 2),
        "natural_fm_yr5_m": round(debt_yr5_m + c_term_m, 2),
    }

    # Step 6: Bankability & Sponsor Verdict Matrix
    if sim["equity_irr_pct"] >= data.target_equity_irr_pct and sim["min_dscr_p90"] >= data.target_dscr_p90:
        verdict = f"BANKABLE & ACCRETIVE (Beats {data.target_equity_irr_pct}% IRR Hurdle & P90 Covenants)"
    elif sim["min_dscr_p90"] >= data.target_dscr_p90:
        verdict = f"LENDER BANKABLE / EQUITY SHORTFALL (Needs ${min_winning_tariff}/MWh Tariff)"
    else:
        verdict = "UNBANKABLE STRUCTURE (Breaches Senior Debt Coverage Covenants)"

    return {
        "regime": data.commercial_regime,
        "total_capex_m": round(sim["total_capex_m"], 2),
        "max_debt_m": round(sim["max_debt_m"], 2),
        "sponsor_equity_m": round(sim["sponsor_equity_m"], 2),
        "actual_gearing_pct": round(gearing * 100.0, 1),
        "binding_constraint": sim["binding_constraint"],
        "debt_by_constraint_m": sim["constraints"],
        "equity_irr_pct": sim["equity_irr_pct"],
        "min_winning_tariff": min_winning_tariff,
        "lcoe_usd_mwh": lcoe_usd_mwh,
        "min_dscr_p90": round(sim["min_dscr_p90"], 2),
        "min_dscr_p50": round(sim["min_dscr_p50"], 2),
        "llcr": round(sim["llcr"], 2),
        "plcr": round(sim["plcr"], 2),
        "breakeven_cf_drop_pct": round(sim["breakeven_cf_drop_pct"], 1),
        "fitch_spread_pct": fitch_spread_pct,
        "fitch_vol_rating": fitch_vol_rating,
        "years": list(range(1, data.ppa_tenor_years + 1)),
        "cfads_p50_m": [round(x, 2) for x in sim["cfads_p50_m"]],
        "cfads_p90_m": [round(x, 2) for x in sim["cfads_p90_m"]],
        "debt_service_m": [round(x, 2) for x in sim["debt_service_m"]],
        "equity_cf_m": [round(x, 2) for x in sim["equity_cf_m"]],
        "buyout_schedule": buyout_schedule,
        "verdict": verdict
    }
