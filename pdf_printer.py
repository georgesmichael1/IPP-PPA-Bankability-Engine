from fpdf import FPDF

def _clean(text: str) -> str:
    """Sanitizes any Unicode characters into strict latin-1 safe ASCII for FPDF Helvetica."""
    replacements = {
        "\u2014": "-",  # em-dash
        "\u2013": "-",  # en-dash
        "\u2212": "-",  # minus sign
        "\u2022": "-",  # bullet
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

def create_pdf_report(
    results: dict,
    waterfall_chart_path: str,
    debt_chart_path: str,
    stress_chart_path: str,
    term_bess_chart_path: str,
    client_id: str = "Standard User",
    output_filename: str = "Streamline_IPP_Report.pdf"
) -> str:
    pdf = FPDF()

    # ================= PAGE 1: CAPITAL STRUCTURE, DEBT SCULPTING & WATERFALL =================
    pdf.add_page()
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.cell(0, 5, _clean(f"Authorized License: {client_id.upper()} | Streamline v3.0 Institutional IPP & BESS Credit Engine"), ln=True, align="R")

    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(0, 8, _clean("IPP & BESS Project Finance Bankability & Credit Memo"), ln=True, align="C")
    pdf.set_font("Helvetica", size=9.5)
    pdf.cell(0, 5.5, _clean(f"Procurement Regime: {results['regime']}  |  Implied Project WACC: {results['wacc_pct']}%"), ln=True, align="C")
    pdf.ln(1.5)

    pdf.set_font("Helvetica", style="B", size=10.5)
    pdf.cell(0, 7, _clean(f"CREDIT COMMITTEE VERDICT: {results['verdict']}"), ln=True)
    pdf.ln(1)

    pdf.set_font("Helvetica", style="B", size=9.5)
    pdf.cell(0, 5.5, _clean("1. Non-Circular Debt Sculpting, Two-Step Auction Solver & Coverage Summary"), ln=True)
    pdf.set_font("Helvetica", size=8.8)
    pdf.cell(0, 5, _clean(f"Total Installed CAPEX: ${results['total_capex_m']:,.2f}M (Gen: ${results['gen_capex_m']:,.2f}M | BESS: ${results['bess_capex_m']:,.2f}M)"), ln=True)
    pdf.cell(0, 5, _clean(f"Supportable Senior Debt: ${results['max_debt_m']:,.2f}M ({results['actual_gearing_pct']}% Gearing)  |  Sponsor Equity: ${results['sponsor_equity_m']:,.2f}M"), ln=True)
    pdf.cell(0, 5, _clean(f"Binding Debt Constraint: {results['binding_constraint']}  |  Bodmer Ratio Rule: {results['bodmer_p99_driver']}"), ln=True)
    pdf.cell(0, 5, _clean(f"6-Month DSRA Target: ${results['dsra_balance_m']:,.2f}M  |  Non-Circular Final Period DS (with DSRA Release): ${results['bodmer_final_ds_m']:,.2f}M"), ln=True)
    pdf.cell(0, 5, _clean(f"Sponsor P50 Equity IRR: {results['equity_irr_pct']}%  |  Min Winning Tariff for Hurdle IRR: ${results['min_winning_tariff']:,.2f}/MWh  |  LCOE: ${results['lcoe_usd_mwh']:,.2f}/MWh"), ln=True)
    pdf.cell(0, 5, _clean(f"Base Coverage: Min P90 DSCR = {results['min_dscr_p90']}x | Min P50 DSCR = {results['min_dscr_p50']}x | Net-Debt LLCR = {results['llcr']}x | PLCR = {results['plcr']}x"), ln=True)
    pdf.ln(2)

    pdf.image(waterfall_chart_path, x=16, w=178)
    pdf.ln(2)
    pdf.image(debt_chart_path, x=20, w=170)

    # ================= PAGE 2: S&P/FITCH STRESS TEST, BESS 3-LEDGER & BUYOUT MATRIX =================
    pdf.add_page()
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.cell(0, 5, _clean(f"Page 2 - Rating Agency Stress Test, BESS 3-Ledger & GSA Termination Matrix | License: {client_id.upper()}"), ln=True, align="R")
    pdf.ln(1)

    pdf.set_font("Helvetica", style="B", size=9.5)
    pdf.cell(0, 5.5, _clean("2. S&P / Fitch Downside Credit Stress Test (1-Yr P99, +25% Deg, -3% Avail, +10-15% O&M)"), ln=True)
    pdf.set_font("Helvetica", size=8.8)
    pdf.cell(0, 5, _clean(f"Workout Diagnostic: {results['stress_workout_status']}"), ln=True)
    pdf.cell(0, 5, _clean(f"Stressed Min DSCR: {results['min_dscr_stress']}x  |  Stressed LLCR: {results['stress_llcr']}x  |  Stressed PLCR: {results['stress_plcr']}x"), ln=True)
    pdf.cell(0, 5, _clean(f"Max Tolerable Cash Flow Haircut Before Default (LLCR=1.0x): -{results['breakeven_cf_drop_pct']}%  |  Fitch P90/P50 Spread: {results['fitch_spread_pct']}% ({results['fitch_vol_rating']})"), ln=True)
    pdf.ln(1.5)

    pdf.set_font("Helvetica", style="B", size=9.5)
    pdf.cell(0, 5.5, _clean("3. BESS 3-Ledger Degradation, LCOS & Year-8 Phased Augmentation Arbitrage"), ln=True)
    pdf.set_font("Helvetica", size=8.8)
    if results["bess_capex_m"] > 0:
        pdf.cell(0, 5, _clean(f"Levelized Cost of Storage (LCOS): ${results['lcos_usd_mwh']:,.2f}/MWh  |  Annual MRA Reserve Funding (Yrs 1-8): ${results['annual_mra_funding_m']:,.2f}M/yr"), ln=True)
        pdf.cell(0, 5, _clean(f"Yr-0 Overbuild CAPEX: ${results['overbuild_capex_m']:,.2f}M vs. Yr-8 Phased Augmentation NPV: ${results['phased_aug_npv_m']:,.2f}M -> Net NPV Savings: ${results['bess_aug_savings_m']:,.2f}M"), ln=True)
    else:
        pdf.cell(0, 5, _clean("No BESS Configured (0 MWh). Tariff Sensitivity Matrix (-10% to +10% PPA Tariff) plotted in lower-right chart."), ln=True)
    pdf.ln(2)

    pdf.image(stress_chart_path, x=16, w=178)
    pdf.ln(2)
    pdf.image(term_bess_chart_path, x=14, w=182)
    pdf.ln(2)

    # Milestone Termination Buyout Table
    pdf.set_font("Helvetica", style="B", size=9.5)
    pdf.cell(0, 5.5, _clean("4. Open Solar Contracts / MENA GSA Early Termination Buyout Schedule ($M)"), ln=True)
    pdf.set_font("Helvetica", size=8.5)
    yr_indices = [0, min(4, len(results["years"]) - 1), min(9, len(results["years"]) - 1), min(14, len(results["years"]) - 1)]
    labels_yr = [f"Yr {idx + 1}" for idx in yr_indices]
    off_vals = " | ".join([f"{labels_yr[i]}: ${results['buyout_offtaker_curve'][idx]:,.1f}M" for i, idx in enumerate(yr_indices)])
    prj_vals = " | ".join([f"{labels_yr[i]}: ${results['buyout_project_curve'][idx]:,.1f}M" for i, idx in enumerate(yr_indices)])
    nfm_vals = " | ".join([f"{labels_yr[i]}: ${results['buyout_fm_curve'][idx]:,.1f}M" for i, idx in enumerate(yr_indices)])

    pdf.cell(0, 4.8, _clean(f"- Sovereign / Offtaker Default (Put Option - Full Debt + Equity + Return):  {off_vals}"), ln=True)
    pdf.cell(0, 4.8, _clean(f"- Prolonged Natural Force Majeure (Shared Remedy - Debt + 50% Equity):  {nfm_vals}"), ln=True)
    pdf.cell(0, 4.8, _clean(f"- Project Company Default (Lender Call Option - Senior Debt + Term Costs):  {prj_vals}"), ln=True)

    pdf.output(output_filename)
    return output_filename
