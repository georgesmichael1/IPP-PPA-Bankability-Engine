from fpdf import FPDF

def create_pdf_report(
    results: dict,
    waterfall_chart_path: str,
    debt_chart_path: str,
    client_id: str = "Standard User",
    output_filename: str = "Streamline_IPP_Report.pdf"
) -> str:
    pdf = FPDF()
    pdf.add_page()

    # License Stamp Header
    pdf.set_font("Helvetica", style="I", size=8.5)
    pdf.cell(0, 5, f"Authorized License: {client_id.upper()} | Streamline IPP & PPA Bankability Engine", ln=True, align="R")
    pdf.ln(1)

    # Title Banner
    pdf.set_font("Helvetica", style="B", size=15)
    pdf.cell(0, 9, "IPP & BESS Project Finance Bankability Memo", ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Commercial Regime: {results['regime']}", ln=True, align="C")
    pdf.ln(2)

    # Executive Verdict
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 8, f"CREDIT COMMITTEE VERDICT: {results['verdict']}", ln=True)
    pdf.ln(1)

    # Section 1: Capital Structure, Auction Tariff Solver & Coverage Covenants
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.cell(0, 6, "1. Capital Structure, Sculpted Debt & Two-Step Tariff Solver Summary", ln=True)
    pdf.set_font("Helvetica", size=9.5)
    pdf.cell(0, 5.5, f"Total Installed CAPEX: ${results['total_capex_m']:,.2f}M  |  Supportable Senior Debt: ${results['max_debt_m']:,.2f}M ({results['actual_gearing_pct']}% Gearing)", ln=True)
    pdf.cell(0, 5.5, f"Sponsor Equity Required: ${results['sponsor_equity_m']:,.2f}M  |  Binding Debt Sizing Wall: {results['binding_constraint']}", ln=True)
    pdf.cell(0, 5.5, f"P50 Sponsor Equity IRR: {results['equity_irr_pct']}%  |  Min Winning Tariff for Target IRR: ${results['min_winning_tariff']:,.2f}/MWh  |  LCOE: ${results['lcoe_usd_mwh']:,.2f}/MWh", ln=True)
    pdf.cell(0, 5.5, f"Min Sculpted DSCR (1-Yr P90): {results['min_dscr_p90']}x  |  Min DSCR (P50): {results['min_dscr_p50']}x  |  LLCR: {results['llcr']}x  |  PLCR: {results['plcr']}x", ln=True)
    pdf.cell(0, 5.5, f"Max Break-Even Cash Flow Haircut (LLCR=1.0x): -{results['breakeven_cf_drop_pct']}%  |  Fitch P90/P50 Spread: {results['fitch_spread_pct']}% ({results['fitch_vol_rating']})", ln=True)
    pdf.ln(2)

    # Visual 1 & Visual 2
    pdf.image(waterfall_chart_path, x=18, w=174)
    pdf.ln(2)
    pdf.image(debt_chart_path, x=22, w=166)
    pdf.ln(3)

    # Section 2: Open Solar Contracts / MENA GSA Put & Call Termination Buyout Ledger
    b = results["buyout_schedule"]
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.cell(0, 6, "2. Contractual Early Termination Buyout Protection (Open Solar Contracts / GSA Formula)", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 5, f"- Sovereign / Offtaker Default (Put Option - Debt + Equity + Return): Yr 1 = ${b['offtaker_default_yr1_m']:,.2f}M  |  Yr 5 = ${b['offtaker_default_yr5_m']:,.2f}M", ln=True)
    pdf.cell(0, 5, f"- Project Company Default (Lender Call Option - Senior Debt + Term Costs): Yr 1 = ${b['project_default_yr1_m']:,.2f}M  |  Yr 5 = ${b['project_default_yr5_m']:,.2f}M", ln=True)
    pdf.cell(0, 5, f"- Prolonged Natural Force Majeure (Neutral Remedy - Senior Debt Protection): Yr 1 = ${b['natural_fm_yr1_m']:,.2f}M  |  Yr 5 = ${b['natural_fm_yr5_m']:,.2f}M", ln=True)

    pdf.output(output_filename)
    return output_filename
