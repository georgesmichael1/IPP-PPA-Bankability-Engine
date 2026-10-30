import importlib
import streamlit as st

import schema
import engine
import chart_factory
import pdf_printer

importlib.reload(schema)
importlib.reload(engine)
importlib.reload(chart_factory)
importlib.reload(pdf_printer)

from schema import IPPAnalysisInput
from engine import analyze_ipp_project
from chart_factory import (
    generate_waterfall_chart,
    generate_debt_sizing_chart,
    generate_stress_dscr_chart,
    generate_termination_and_bess_chart
)
from pdf_printer import create_pdf_report

st.set_page_config(page_title="Streamline v3.0 IPP & BESS Engine", layout="wide")
st.title("⚡ Streamline v3.0: Institutional IPP & BESS Project Finance Engine")
st.markdown(
    "Non-circular multi-criteria debt sculpting (P50/P90/P99), Two-Step Auction Tariff Solver, "
    "S&P/Fitch Downside Credit Stress Testing, 3-Ledger BESS Augmentation & LCOS, and GSA Termination Valuation."
)

url_client = st.query_params.get("client", "")

with st.form("ipp_form"):
    st.subheader("1. Commercial Regime, Generation & Co-Located / Standalone BESS Sizing")
    c1, c2, c3, c4 = st.columns(4)
    commercial_regime = c1.selectbox(
        "MENA Procurement Regime",
        [
            "Solar PV BOO PPA (MENA Single-Buyer)",
            "Wind BOO PPA (EETC / SPPC Standard)",
            "Standalone BESS Tolling SSA (SPPC 15-Yr)",
            "24/7 Baseload RTC PV+BESS PPA (EWEC Standard)"
        ]
    )
    capacity_mw = c2.number_input("Generation Capacity (MW)", min_value=1.0, value=200.0, step=10.0)
    bess_capacity_mwh = c3.number_input("BESS Storage Capacity (MWh)", min_value=0.0, value=100.0, step=20.0)
    base_availability_pct = c4.number_input("Guaranteed Availability (%)", min_value=70.0, max_value=100.0, value=98.5, step=0.5)

    st.subheader("2. CAPEX, O&M & Exceedance Resource Profile (P50 / 1-Yr P90 / 1-Yr P99)")
    c5, c6, c7, c8 = st.columns(4)
    capex_per_kw = c5.number_input("Gen Installed Cost ($/kW)", min_value=100.0, value=690.0, step=10.0)
    bess_capex_per_kwh = c6.number_input("BESS Installed Cost ($/kWh)", min_value=0.0, value=192.0, step=10.0)
    fixed_om_per_kw_yr = c7.number_input("Fixed Gen O&M ($/kW-yr)", min_value=0.0, value=11.5, step=0.5)
    annual_degradation_pct = c8.number_input("Gen Degradation (%/yr)", min_value=0.0, max_value=5.0, value=0.50, step=0.05)

    c9, c10, c11, c12 = st.columns(4)
    p50_cf_pct = c9.number_input("P50 Base Capacity Factor (%)", min_value=5.0, max_value=95.0, value=28.5, step=0.5)
    p90_1yr_cf_pct = c10.number_input("1-Yr P90 Capacity Factor (%)", min_value=5.0, max_value=95.0, value=26.2, step=0.5)
    p99_1yr_cf_pct = c11.number_input("1-Yr P99 Capacity Factor (%)", min_value=5.0, max_value=95.0, value=23.5, step=0.5)
    ppa_tariff_usd_mwh = c12.number_input("Bid PPA Tariff ($/MWh)", min_value=1.0, value=32.0, step=0.5)

    st.subheader("3. BESS 3-Ledger Degradation & Duty Cycle Parameters")
    b1, b2, b3, b4, b5 = st.columns(5)
    bess_cycles_per_yr = int(b1.number_input("Annual Full Cycles", min_value=0, max_value=1000, value=350, step=10))
    bess_dod_pct = b2.number_input("Depth of Discharge (%)", min_value=20.0, max_value=100.0, value=90.0, step=2.5)
    bess_initial_rte_pct = b3.number_input("Initial RTE (%)", min_value=60.0, max_value=98.0, value=88.0, step=0.5)
    bess_annual_energy_fade_pct = b4.number_input("Meter Energy Fade (%/yr)", min_value=0.0, max_value=8.0, value=2.10, step=0.1)
    bess_charging_cost_mwh = b5.number_input("Charging Cost ($/MWh)", min_value=0.0, value=22.0, step=1.0)

    st.subheader("4. Non-Recourse Debt Covenants & Sponsor Hurdle")
    c13, c14, c15, c16 = st.columns(4)
    ppa_tenor_years = int(c13.number_input("PPA Tenor (Years)", min_value=5, max_value=35, value=25, step=1))
    debt_tenor_years = int(c14.number_input("Debt Tenor (Years)", min_value=3, max_value=30, value=18, step=1))
    interest_rate_pct = c15.number_input("All-In Interest Rate (%)", min_value=1.0, max_value=25.0, value=6.5, step=0.25)
    max_gearing_pct = c16.number_input("Max Gearing Cap (%)", min_value=10.0, max_value=95.0, value=80.0, step=2.5)

    c17, c18, c19, c20 = st.columns(4)
    target_dscr_p50 = c17.number_input("Target P50 DSCR (x)", min_value=1.00, max_value=2.50, value=1.35, step=0.05)
    target_dscr_p90 = c18.number_input("Target 1-Yr P90 DSCR (x)", min_value=1.00, max_value=2.50, value=1.20, step=0.05)
    target_dscr_p99 = c19.number_input("1-Yr P99 Breakeven DSCR (x)", min_value=0.80, max_value=2.00, value=1.00, step=0.05)
    target_equity_irr_pct = c20.number_input("Sponsor Hurdle Equity IRR (%)", min_value=1.0, max_value=40.0, value=12.0, step=0.5)

    submitted = st.form_submit_button("Run Full Institutional Simulation & Stress Test (Free Preview)")

if submitted:
    data = IPPAnalysisInput(
        commercial_regime=commercial_regime,
        capacity_mw=capacity_mw,
        bess_capacity_mwh=bess_capacity_mwh,
        capex_per_kw=capex_per_kw,
        bess_capex_per_kwh=bess_capex_per_kwh,
        fixed_om_per_kw_yr=fixed_om_per_kw_yr,
        p50_cf_pct=p50_cf_pct,
        p90_1yr_cf_pct=p90_1yr_cf_pct,
        p99_1yr_cf_pct=p99_1yr_cf_pct,
        base_availability_pct=base_availability_pct,
        annual_degradation_pct=annual_degradation_pct,
        bess_cycles_per_yr=bess_cycles_per_yr,
        bess_dod_pct=bess_dod_pct,
        bess_initial_rte_pct=bess_initial_rte_pct,
        bess_annual_energy_fade_pct=bess_annual_energy_fade_pct,
        bess_charging_cost_mwh=bess_charging_cost_mwh,
        ppa_tariff_usd_mwh=ppa_tariff_usd_mwh,
        ppa_tenor_years=ppa_tenor_years,
        debt_tenor_years=debt_tenor_years,
        interest_rate_pct=interest_rate_pct,
        max_gearing_pct=max_gearing_pct,
        target_dscr_p50=target_dscr_p50,
        target_dscr_p90=target_dscr_p90,
        target_dscr_p99=target_dscr_p99,
        target_equity_irr_pct=target_equity_irr_pct
    )
    st.session_state["ipp_data"] = data
    st.session_state["ipp_results"] = analyze_ipp_project(data)

if "ipp_results" in st.session_state:
    res = st.session_state["ipp_results"]

    st.divider()
    st.subheader("📊 Executive Deal Desk & Credit Rating Stress Summary")
    st.info(f"**CREDIT COMMITTEE VERDICT:** {res['verdict']}  \n**S&P / FITCH STRESS WORKOUT:** {res['stress_workout_status']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sponsor P50 Equity IRR", f"{res['equity_irr_pct']}%")
    m2.metric("Min Winning Auction Tariff", f"${res['min_winning_tariff']}/MWh")
    m3.metric("Supportable Senior Debt", f"${res['max_debt_m']}M ({res['actual_gearing_pct']}%)")
    m4.metric("Binding Debt Sizing Wall", res["binding_constraint"])

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Net-Debt LLCR / PLCR", f"{res['llcr']}x / {res['plcr']}x")
    m6.metric("S&P/Fitch Stressed Min DSCR", f"{res['min_dscr_stress']}x")
    m7.metric("Generation LCOE", f"${res['lcoe_usd_mwh']}/MWh")
    m8.metric("BESS LCOS / Aug NPV Savings", f"${res['lcos_usd_mwh']}/MWh | +${res['bess_aug_savings_m']}M")

    # Generate all 4 institutional charts and preview on dashboard
    wf_path = generate_waterfall_chart(res, filename="cloud_ipp_waterfall.png")
    debt_path = generate_debt_sizing_chart(res, filename="cloud_ipp_debt.png")
    stress_path = generate_stress_dscr_chart(res, filename="cloud_ipp_stress.png")
    term_bess_path = generate_termination_and_bess_chart(res, filename="cloud_ipp_term_bess.png")

    st.subheader("📈 Institutional Visual Analytics Suite (4-Chart Preview)")
    g1, g2 = st.columns(2)
    g1.image(wf_path, use_container_width=True)
    g2.image(debt_path, use_container_width=True)

    g3, g4 = st.columns(2)
    g3.image(stress_path, use_container_width=True)
    g4.image(term_bess_path, use_container_width=True)

    st.divider()
    st.subheader("🔒 Unlock Official 2-Page Institutional Credit & Bankability PDF")
    st.caption(
        "Compiles all 4 high-resolution charts, Bodmer DSRA release diagnostics, S&P/Fitch downside stress metrics, "
        "BESS Year-8 Augmentation MRA schedules, and the 25-year Open Solar Contracts / GSA Termination Buyout Ledger."
    )

    access_key = st.text_input(
        "Enter Monthly Client ID or Single-Report Ticket:",
        value=url_client,
        placeholder="e.g., george_vip or elsewedy_demo"
    ).strip()

    if access_key:
        clients_db = st.secrets.get("clients", {})
        tickets_db = st.secrets.get("single_tickets", {})
        status = clients_db.get(access_key, tickets_db.get(access_key, None))

        if status == 1:
            st.success(f"License Verified ({access_key}). Compiling 2-Page Institutional Credit Memo...")
            create_pdf_report(
                res,
                waterfall_chart_path=wf_path,
                debt_chart_path=debt_path,
                stress_chart_path=stress_path,
                term_bess_chart_path=term_bess_path,
                client_id=access_key,
                output_filename="Streamline_IPP_Credit_Memo_v3.pdf"
            )

            with open("Streamline_IPP_Credit_Memo_v3.pdf", "rb") as pdf_file:
                st.download_button(
                    label="📄 Download 2-Page Official IPP Credit & Bankability Memo (PDF)",
                    data=pdf_file,
                    file_name=f"Streamline_IPP_Memo_v3_{access_key}.pdf",
                    mime="application/pdf"
                )
        elif status == 0:
            st.error("⛔ Access Deactivated (Status = 0). Your subscription or ticket has expired.")
        else:
            st.warning("⚠️ Invalid Client ID or Ticket Code. Please verify your license key.")
