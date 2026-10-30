from schema import IPPAnalysisInput

def _npv(rate: float, values: list) -> float:
    return sum(v / ((1.0 + rate) ** (t + 1)) for t, v in enumerate(values))

def _calc_irr(cf: list) -> float:
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

    # Fixed O&M + BESS Fixed O&M ($5.5/kWh-yr benchmark) + Extended Warranty (1.0% of BESS CAPEX from Yr 3)
    gen_om_m = (data.capacity_mw * 1000.0 * data.fixed_om_per_kw_yr) / 1e6
    bess_om_m = (data.bess_capacity_mwh * 1000.0 * 5.5) / 1e6
    base_annual_om_m = gen_om_m + bess_om_m

    # S&P / Fitch Downside Stress Parameters:
    # +25% relative degradation stress, -3% absolute availability stress, +10% Solar / +15% Wind O&M stress
    is_wind = "Wind" in data.commercial_regime
    om_stress_mult = 1.15 if is_wind else 1.10
    stress_deg = (data.annual_degradation_pct * 1.25) / 100.0
    stress_avail_ratio = max(0.50, (data.base_availability_pct - 3.0) / data.base_availability_pct)

    n_ppa = data.ppa_tenor_years
    n_debt = min(data.debt_tenor_years, n_ppa)
    deg = data.annual_degradation_pct / 100.0
    avail = data.base_availability_pct / 100.0
    r_d = data.interest_rate_pct / 100.0

    # BESS Augmentation Reserve (MRA) Funding if BESS > 0 (Year-8 Phased Augmentation at $165/kWh projected 2030 cost)
    aug_capex_yr8_m = (data.bess_capacity_mwh * 0.22 * 1000.0 * 165.0) / 1e6 if data.bess_capacity_mwh > 0 else 0.0
    annual_mra_funding_m = (aug_capex_yr8_m / 8.0) if data.bess_capacity_mwh > 0 else 0.0

    gen_p50_mwh, cfads_p50_m, cfads_p90_m, cfads_p99_m, cfads_stress_m, om_series_m = [], [], [], [], [], []

    for yr in range(1, n_ppa + 1):
        deg_factor = (1.0 - deg) ** (yr - 1)
        stress_deg_factor = (1.0 - stress_deg) ** (yr - 1)

        # Extended warranty kicks in at Year 3 (1.1% of BESS CAPEX) + MRA funding Years 1-8
        ext_warranty_m = (bess_capex_m * 0.011) if (yr >= 3 and data.bess_capacity_mwh > 0) else 0.0
        mra_m = annual_mra_funding_m if (yr <= 8 and data.bess_capacity_mwh > 0) else 0.0
        yr_om_m = base_annual_om_m + ext_warranty_m + mra_m
        yr_stress_om_m = (base_annual_om_m * om_stress_mult) + ext_warranty_m + mra_m
        om_series_m.append(yr_om_m)

        mwh_50 = data.capacity_mw * 8760.0 * (data.p50_cf_pct / 100.0) * avail * deg_factor
        mwh_90 = data.capacity_mw * 8760.0 * (data.p90_1yr_cf_pct / 100.0) * avail * deg_factor
        mwh_99 = data.capacity_mw * 8760.0 * (data.p99_1yr_cf_pct / 100.0) * avail * deg_factor
        mwh_stress = data.capacity_mw * 8760.0 * (data.p99_1yr_cf_pct / 100.0) * (avail * stress_avail_ratio) * stress_deg_factor

        gen_p50_mwh.append(mwh_50)
        cfads_p50_m.append(max(0.0, (mwh_50 * tariff_usd_mwh / 1e6) - yr_om_m))
        cfads_p90_m.append(max(0.0, (mwh_90 * tariff_usd_mwh / 1e6) - yr_om_m))
        cfads_p99_m.append(max(0.0, (mwh_99 * tariff_usd_mwh / 1e6) - yr_om_m))
        cfads_stress_m.append(max(0.0, (mwh_stress * tariff_usd_mwh / 1e6) - yr_stress_om_m))

    # 2. Bodmer Multi-Criteria Non-Circular Debt Sizing
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

    # 3. Sculpted Debt Schedule + 6-Month DSRA Ledger
    scale_factor = (max_debt_m / debt_p90_m) if debt_p90_m > 0 else 0.0
    debt_service_m, interest_series_m, principal_series_m, debt_balance_m = [], [], [], []
    rem_debt = max_debt_m

    for t in range(n_ppa):
        if t < n_debt and rem_debt > 1e-6:
            interest_m = rem_debt * r_d
            sculpted_ds = target_ds_p90[t] * scale_factor
            principal_m = max(0.0, min(rem_debt, sculpted_ds - interest_m))
            actual_ds = interest_m + principal_m
            rem_debt = max(0.0, rem_debt - principal_m)
        else:
            interest_m, principal_m, actual_ds = 0.0, 0.0, 0.0
        interest_series_m.append(interest_m)
        principal_series_m.append(principal_m)
        debt_service_m.append(actual_ds)
        debt_balance_m.append(rem_debt)

    # 6-Month DSRA Target (50% of Year 1 Debt Service) & Bodmer Non-Circular Final Release
    dsra_balance_m = round(debt_service_m[0] * 0.50, 2) if debt_service_m else 0.0
    bodmer_final_ds_m = round(cfads_p90_m[n_debt - 1] / max(0.1, (data.target_dscr_p90 - 1.0)), 2)

    # 4. Coverage Ratios (Base P50, Lender P90, and S&P/Fitch Downside Stress)
    dscr_p50_series, dscr_p90_series, dscr_stress_series = [], [], []
    for t in range(n_debt):
        ds = debt_service_m[t]
        if ds > 1e-4:
            dscr_p50_series.append(round(cfads_p50_m[t] / ds, 2))
            dscr_p90_series.append(round(cfads_p90_m[t] / ds, 2))
            dscr_stress_series.append(round(cfads_stress_m[t] / ds, 2))
        else:
            dscr_p50_series.append(0.0)
            dscr_p90_series.append(0.0)
            dscr_stress_series.append(0.0)

    equity_cf_m = [-sponsor_equity_m] + [cfads_p50_m[t] - debt_service_m[t] for t in range(n_ppa)]
    equity_irr_pct = _calc_irr(equity_cf_m)

    # Net-Debt LLCR & PLCR (Accounting for DSRA as Negative Debt per Bodmer)
    net_debt_m = max(0.01, max_debt_m - dsra_balance_m)
    llcr = (_npv(r_d, cfads_p50_m[:n_debt]) / net_debt_m) if max_debt_m > 0 else 0.0
    plcr = (_npv(r_d, cfads_p50_m) / net_debt_m) if max_debt_m > 0 else 0.0
    stress_llcr = (_npv(r_d, cfads_stress_m[:n_debt]) / net_debt_m) if max_debt_m > 0 else 0.0
    stress_plcr = (_npv(r_d, cfads_stress_m) / net_debt_m) if max_debt_m > 0 else 0.0
    breakeven_cf_drop_pct = max(0.0, ((llcr - 1.0) / llcr) * 100.0) if llcr > 1.0 else 0.0

    return {
        "total_capex_m": total_capex_m,
        "gen_capex_m": gen_capex_m,
        "bess_capex_m": bess_capex_m,
        "max_debt_m": max_debt_m,
        "sponsor_equity_m": sponsor_equity_m,
        "dsra_balance_m": dsra_balance_m,
        "bodmer_final_ds_m": bodmer_final_ds_m,
        "binding_constraint": binding_constraint,
        "constraints": {k: round(v, 2) for k, v in constraints.items()},
        "equity_irr_pct": equity_irr_pct,
        "dscr_p50_series": dscr_p50_series,
        "dscr_p90_series": dscr_p90_series,
        "dscr_stress_series": dscr_stress_series,
        "min_dscr_p90": min(dscr_p90_series) if dscr_p90_series else 0.0,
        "min_dscr_p50": min(dscr_p50_series) if dscr_p50_series else 0.0,
        "min_dscr_stress": min(dscr_stress_series) if dscr_stress_series else 0.0,
        "llcr": llcr,
        "plcr": plcr,
        "stress_llcr": stress_llcr,
        "stress_plcr": stress_plcr,
        "breakeven_cf_drop_pct": breakeven_cf_drop_pct,
        "gen_p50_mwh": gen_p50_mwh,
        "cfads_p50_m": cfads_p50_m,
        "cfads_p90_m": cfads_p90_m,
        "cfads_stress_m": cfads_stress_m,
        "debt_service_m": debt_service_m,
        "interest_series_m": interest_series_m,
        "principal_series_m": principal_series_m,
        "debt_balance_m": debt_balance_m,
        "equity_cf_m": equity_cf_m[1:],
        "om_series_m": om_series_m,
        "aug_capex_yr8_m": aug_capex_yr8_m,
        "annual_mra_funding_m": annual_mra_funding_m
    }

def analyze_ipp_project(data: IPPAnalysisInput) -> dict:
    # 1. Base Capital Structure Simulation
    sim = _simulate_capital_structure(data, data.ppa_tariff_usd_mwh)

    # 2. Two-Step Institutional Auction Tariff Solver
    low_t, high_t = 5.0, 250.0
    for _ in range(45):
        mid_t = (low_t + high_t) / 2.0
        test_irr = _simulate_capital_structure(data, mid_t)["equity_irr_pct"]
        if test_irr < data.target_equity_irr_pct:
            low_t = mid_t
        else:
            high_t = mid_t
    min_winning_tariff = round((low_t + high_t) / 2.0, 2)

    # 3. Implied WACC, LCOE & Emerging Market WACC Sensitivity
    gearing = sim["max_debt_m"] / sim["total_capex_m"] if sim["total_capex_m"] > 0 else 0.0
    wacc = (gearing * (data.interest_rate_pct / 100.0)) + ((1.0 - gearing) * (data.target_equity_irr_pct / 100.0))
    pv_costs_m = sim["total_capex_m"] + _npv(wacc, sim["om_series_m"])
    pv_energy_mwh = _npv(wacc, sim["gen_p50_mwh"])
    lcoe_usd_mwh = round((pv_costs_m * 1e6) / pv_energy_mwh, 2) if pv_energy_mwh > 0 else 0.0

    # Bodmer P99 vs P50 Mathematical Decision Rule
    p99_p50_ratio = round(data.p99_1yr_cf_pct / data.p50_cf_pct, 4)
    dscr_ratio_threshold = round(data.target_dscr_p99 / data.target_dscr_p50, 4)
    bodmer_p99_driver = (
        f"P99 Drives Debt (P99/P50={p99_p50_ratio:.2f} < {dscr_ratio_threshold:.2f})"
        if p99_p50_ratio < dscr_ratio_threshold
        else f"P50/P90 Drives Debt (P99/P50={p99_p50_ratio:.2f} >= {dscr_ratio_threshold:.2f})"
    )

    # 4. 3-Ledger BESS Degradation, RTE Decay (-0.22%/yr) & Institutional LCOS Engine
    bess_Retention_overbuild, bess_Retention_aug, bess_rte_series = [], [], []
    bess_net_mwh_series, bess_cost_series_m = [], []
    cap_0 = data.bess_capacity_mwh
    fade_rate = data.bess_annual_energy_fade_pct / 100.0
    avail_bess = data.base_availability_pct / 100.0

    for yr in range(1, data.ppa_tenor_years + 1):
        # Strategy A: Year-0 Overbuild (starts at 118% nameplate, decays continuously)
        ret_overbuild = max(60.0, 118.0 * ((1.0 - fade_rate) ** (yr - 1)))
        # Strategy B: Year-8 Phased Augmentation (restores +18% usable energy at Year 8)
        raw_ret = 100.0 * ((1.0 - fade_rate) ** (yr - 1))
        ret_aug = min(104.0, raw_ret + (18.0 if yr >= 8 else 0.0))
        # RTE degrades by 0.22 percentage points per year
        rte_t = max(70.0, data.bess_initial_rte_pct - (0.22 * (yr - 1)))

        bess_Retention_overbuild.append(round(ret_overbuild, 1))
        bess_Retention_aug.append(round(ret_aug, 1))
        bess_rte_series.append(round(rte_t, 2))

        if cap_0 > 0:
            net_mwh = cap_0 * (ret_aug / 100.0) * (data.bess_dod_pct / 100.0) * data.bess_cycles_per_yr * avail_bess
            charge_cost_m = ((net_mwh / (rte_t / 100.0)) * data.bess_charging_cost_mwh) / 1e6
            aug_outflow_m = sim["aug_capex_yr8_m"] if yr == 8 else 0.0
            bess_om_yr_m = (cap_0 * 1000.0 * 5.5) / 1e6
            bess_net_mwh_series.append(net_mwh)
            bess_cost_series_m.append(bess_om_yr_m + charge_cost_m + aug_outflow_m)

    if cap_0 > 0 and sum(bess_net_mwh_series) > 0:
        pv_bess_tco_m = sim["bess_capex_m"] + _npv(wacc, bess_cost_series_m)
        pv_bess_mwh = _npv(wacc, bess_net_mwh_series)
        lcos_usd_mwh = round((pv_bess_tco_m * 1e6) / pv_bess_mwh, 2)
        overbuild_capex_m = round(sim["bess_capex_m"] * 1.18, 2)
        phased_aug_npv_m = round(sim["bess_capex_m"] + (sim["aug_capex_yr8_m"] / ((1.0 + wacc) ** 8)), 2)
        bess_aug_savings_m = round(overbuild_capex_m - phased_aug_npv_m, 2)
    else:
        lcos_usd_mwh, overbuild_capex_m, phased_aug_npv_m, bess_aug_savings_m = 0.0, 0.0, 0.0, 0.0

    # 5. Full 25-Year Open Solar Contracts / MENA GSA Termination Buyout Curves
    c_term_m = round(sim["om_series_m"][0] * 0.50, 2)
    eq_return_m = round(sim["sponsor_equity_m"] * ((1.0 + (data.target_equity_irr_pct / 100.0)) ** 3 - 1.0), 2)

    buyout_offtaker_curve, buyout_project_curve, buyout_fm_curve = [], [], []
    for t in range(data.ppa_tenor_years):
        d_out = sim["debt_balance_m"][t] if t > 0 else sim["max_debt_m"]
        # Unamortized shareholder equity decays linearly over PPA life
        sh_out = sim["sponsor_equity_m"] * (1.0 - (t / data.ppa_tenor_years))
        buyout_offtaker_curve.append(round(d_out + sh_out + eq_return_m + c_term_m, 2))
        buyout_project_curve.append(round(d_out + c_term_m, 2))
        buyout_fm_curve.append(round(d_out + (0.5 * sh_out) + c_term_m, 2))

    # 6. Tariff Sensitivity Matrix (-10%, -5%, Base, +5%, +10% Tariff)
    tariff_sens_labels, tariff_sens_irrs = [], []
    for mult in [0.90, 0.95, 1.00, 1.05, 1.10]:
        t_val = round(data.ppa_tariff_usd_mwh * mult, 2)
        irr_val = _simulate_capital_structure(data, t_val)["equity_irr_pct"]
        tariff_sens_labels.append(f"${t_val}/MWh")
        tariff_sens_irrs.append(irr_val)

    # 7. Credit Rating Workout & Fitch Spread Diagnostics
    fitch_spread_pct = round((1.0 - (data.p90_1yr_cf_pct / data.p50_cf_pct)) * 100.0, 2)
    if fitch_spread_pct <= 6.0:
        fitch_vol_rating = "STRONGER (<=6% Spread)"
    elif fitch_spread_pct <= 16.0:
        fitch_vol_rating = "MIDRANGE (6%-16% - BBB Grade)"
    else:
        fitch_vol_rating = "WEAKER (>16% Spread)"

    if sim["stress_llcr"] >= 1.00:
        stress_workout_status = f"SURVIVES S&P/FITCH DOWNSIDE (Stressed LLCR = {sim['stress_llcr']:.2f}x >= 1.00x)"
    elif sim["stress_plcr"] >= 1.00:
        stress_workout_status = f"TENOR EXTENSION WORKOUT VIABLE (Stressed LLCR={sim['stress_llcr']:.2f}x < 1.0x, PLCR={sim['stress_plcr']:.2f}x > 1.0x)"
    else:
        stress_workout_status = f"STRUCTURAL DEFAULT UNDER STRESS (Stressed PLCR = {sim['stress_plcr']:.2f}x < 1.00x)"

    if sim["equity_irr_pct"] >= data.target_equity_irr_pct and sim["min_dscr_p90"] >= data.target_dscr_p90:
        verdict = f"BANKABLE & ACCRETIVE (Beats {data.target_equity_irr_pct}% IRR Hurdle & P90 Covenants)"
    elif sim["min_dscr_p90"] >= data.target_dscr_p90:
        verdict = f"LENDER BANKABLE / EQUITY SHORTFALL (Needs ${min_winning_tariff}/MWh Tariff)"
    else:
        verdict = "UNBANKABLE STRUCTURE (Breaches Senior Debt Coverage Covenants)"

    return {
        "regime": data.commercial_regime,
        "total_capex_m": round(sim["total_capex_m"], 2),
        "gen_capex_m": round(sim["gen_capex_m"], 2),
        "bess_capex_m": round(sim["bess_capex_m"], 2),
        "max_debt_m": round(sim["max_debt_m"], 2),
        "sponsor_equity_m": round(sim["sponsor_equity_m"], 2),
        "dsra_balance_m": sim["dsra_balance_m"],
        "bodmer_final_ds_m": sim["bodmer_final_ds_m"],
        "actual_gearing_pct": round(gearing * 100.0, 1),
        "wacc_pct": round(wacc * 100.0, 2),
        "binding_constraint": sim["binding_constraint"],
        "bodmer_p99_driver": bodmer_p99_driver,
        "debt_by_constraint_m": sim["constraints"],
        "equity_irr_pct": sim["equity_irr_pct"],
        "min_winning_tariff": min_winning_tariff,
        "lcoe_usd_mwh": lcoe_usd_mwh,
        "lcos_usd_mwh": lcos_usd_mwh,
        "overbuild_capex_m": overbuild_capex_m,
        "phased_aug_npv_m": phased_aug_npv_m,
        "bess_aug_savings_m": bess_aug_savings_m,
        "annual_mra_funding_m": round(sim["annual_mra_funding_m"], 2),
        "min_dscr_p90": round(sim["min_dscr_p90"], 2),
        "min_dscr_p50": round(sim["min_dscr_p50"], 2),
        "min_dscr_stress": round(sim["min_dscr_stress"], 2),
        "llcr": round(sim["llcr"], 2),
        "plcr": round(sim["plcr"], 2),
        "stress_llcr": round(sim["stress_llcr"], 2),
        "stress_plcr": round(sim["stress_plcr"], 2),
        "stress_workout_status": stress_workout_status,
        "breakeven_cf_drop_pct": round(sim["breakeven_cf_drop_pct"], 1),
        "fitch_spread_pct": fitch_spread_pct,
        "fitch_vol_rating": fitch_vol_rating,
        "years": list(range(1, data.ppa_tenor_years + 1)),
        "debt_years": list(range(1, len(sim["dscr_p90_series"]) + 1)),
        "cfads_p50_m": [round(x, 2) for x in sim["cfads_p50_m"]],
        "cfads_p90_m": [round(x, 2) for x in sim["cfads_p90_m"]],
        "cfads_stress_m": [round(x, 2) for x in sim["cfads_stress_m"]],
        "debt_service_m": [round(x, 2) for x in sim["debt_service_m"]],
        "interest_series_m": [round(x, 2) for x in sim["interest_series_m"]],
        "principal_series_m": [round(x, 2) for x in sim["principal_series_m"]],
        "debt_balance_m": [round(x, 2) for x in sim["debt_balance_m"]],
        "equity_cf_m": [round(x, 2) for x in sim["equity_cf_m"]],
        "dscr_p50_series": sim["dscr_p50_series"],
        "dscr_p90_series": sim["dscr_p90_series"],
        "dscr_stress_series": sim["dscr_stress_series"],
        "bess_retention_overbuild": bess_Retention_overbuild,
        "bess_retention_aug": bess_Retention_aug,
        "bess_rte_series": bess_rte_series,
        "buyout_offtaker_curve": buyout_offtaker_curve,
        "buyout_project_curve": buyout_project_curve,
        "buyout_fm_curve": buyout_fm_curve,
        "tariff_sens_labels": tariff_sens_labels,
        "tariff_sens_irrs": tariff_sens_irrs,
        "verdict": verdict
    }
