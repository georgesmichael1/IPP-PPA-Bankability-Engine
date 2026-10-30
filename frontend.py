import importlib
import streamlit as st

import schema
import engine
import chart_factory
import pdf_printer

# Force Streamlit Cloud to reload updated modules immediately without cache errors
importlib.reload(schema)
importlib.reload(engine)
importlib.reload(chart_factory)
importlib.reload(pdf_printer)

from schema import IPPAnalysisInput
from engine import analyze_ipp_project
from chart_factory import generate_waterfall_chart, generate_debt_sizing_chart
from pdf_printer import create_pdf_report

st.set_page_config(page_title="Streamline IPP Bankability Engine", layout="wide")
st.title("⚡ Streamline: IPP & BESS Project Finance Engine")
st.markdown(
    "Institutional non-circular debt sculpting (P50/P90/P99), two-step auction tariff optimization, "
    "and Open Solar Contracts / MENA GSA termination buyout modeling."
)

url_client = st.query_params.get("client", "")

with st.form("ipp_form"):
    st.subheader("1. Commercial Regime & Plant Sizing")
    c1, c2, c3 = st.columns(3)
    commercial_regime = c1.selectbox(
        "MENA Procurement Regime",
        [
            "Solar PV BOO PPA (MENA Single-Buyer)",
            "Wind BOO PPA (EETC / SPPC Standard)",
            "Standalone BESS Tolling SSA (SPPC 15-Yr)",
            "24/7 Baseload RTC PV+BESS PPA (EWEC Standard)"
        ]
    )
    capacity_mw = c2.number_input("Generation Nameplate Capacity (MW)", min_value=1.0, value=200.0, step=10.0)
    bess_capacity_mwh = c3.number_input("Co-Located / Standalone BESS (MWh)", min_value=0.0, value=0.0, step=20.0)

    st.subheader("2. CAPEX, O&M & Exceedance Resource Profile (P50 / P90 / P99)")
    c4, c5, c6, c7 = st.columns(4)
    capex_per_kw = c4.number_input("Gen Installed Cost ($/kW)", min_value=100.0, value=690.0, step=10.0)
    bess_capex_per_kwh = c5.number_input("BESS Cost ($/kWh)", min_value=0.0, value=192.0, step=10.0)
    fixed_om_per_kw_yr = c6.number_input("Fixed O&M ($/kW-yr)", min_value=0.0, value=11.5, step=0.5)
    annual_degradation_pct = c7.number_input("System Degradation (%/yr)", min_value=0.0, max_value=5.0, value=0.50, step=0.05)

    c8, c9, c10, c11 = st.columns(4)
    p50_cf_pct = c8.number_input("P50 Base Capacity Factor (%)", min_value=5.0, max_value=95.0, value=28.5, step=0.5)
    p90_1yr_cf_pct = c9.number_input("1-Yr P90 Capacity Factor (%)", min_value=5.0, max_value=95.0, value=26.2, step=0.5)
    p99_1yr_cf_pct = c10.number_input("1-Yr P99 Capacity Factor (%)", min_value=5.0, max_value=95.0, value=23.5, step=0.5)
    ppa_tariff_usd_mwh = c11.number_input("Bid PPA Tariff ($/MWh)", min_value=1.0, value=28.0, step=0.5)

    st.subheader("3. Non-Recourse Debt Covenants & Sponsor Hurdle")
    c12, c13, c14, c15 = st.columns(4)
    ppa_tenor_years = int(c12.number_input("PPA Tenor (Years)", min_value=5, max_value=35, value=25, step=1))
    debt_tenor_years = int(c13.number_input("Debt Tenor (Years)", min_value=3, max_value=30, value=18, step=1))
    interest_rate_pct = c14.number_input("All-In Debt Interest Rate (%)", min_value=1.0, max_value=25.0, value=6.5, step=0.25)
    max_gearing_pct = c15.number_input("Max Gearing Cap (%)", min_value=10.0, max_value=95.0, value=80.0, step=2.5)

    c16, c17, c18, c19 = st.columns(4)
    target_dscr_p50 = c16.number_input("Target P50 DSCR (x)", min_value=1.00, max_value=2.50, value=1.35, step=0.05)
    target_dscr_p90 = c17.number_input("Target 1-Yr P90 DSCR (x)", min_value=1.00, max_value=2.50, value=1.20, step=0.05)
    target_dscr_p99 = c18.number_input("1-Yr P99 Breakeven DSCR (x)", min_value=0.80, max_value=2.00, value=1.00, step=0.05)
    target_equity_irr_pct = c19.number_input("Sponsor Target Equity IRR (%)", min_value=1.0, max_value=40.0, value=12.0, step=0.5)

    submitted = st.form_submit_button("Run Non-Circular Debt Sculptor & Tariff Solver (Free Preview)")

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
        annual_degradation_pct=annual_degradation_pct,
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
    st.subheader("📊 Instant Deal Desk Teaser")
    st.info(f"**CREDIT COMMITTEE VERDICT:** {res['verdict']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sponsor Equity IRR (P50)", f"{res['equity_irr_pct']}%")
    m2.metric("Min Winning Auction Tariff", f"${res['min_winning_tariff']}/MWh")
    m3.metric("Supportable Senior Debt", f"${res['max_debt_m']}M ({res['actual_gearing_pct']}%)")
    m4.metric("Binding Debt Constraint", res["binding_constraint"])

    st.divider()
    st.subheader("🔒 Unlock Full Institutional Credit Memo & Bankability PDF")
    st.caption(
        "Includes 25-Year Sculpted Debt Waterfall Chart, Multi-Criteria P50/P90/P99 Debt Wall Analysis, "
        "LLCR/PLCR Break-Even Stress Haircuts, and Open Solar Contracts Put/Call Termination Buyout Schedule."
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
            st.success(f"License Verified ({access_key}). Compiling Institutional IPP Credit Memo...")

            wf_path = generate_waterfall_chart(res, filename="cloud_ipp_waterfall.png")
            debt_path = generate_debt_sizing_chart(res, filename="cloud_ipp_debt.png")
            create_pdf_report(
                res,
                waterfall_chart_path=wf_path,
                debt_chart_path=debt_path,
                client_id=access_key,
                output_filename="Streamline_IPP_Credit_Memo.pdf"
            )

            with open("Streamline_IPP_Credit_Memo.pdf", "rb") as pdf_file:
                st.download_button(
                    label="📄 Download Official IPP Bankability & Credit Memo (PDF)",
                    data=pdf_file,
                    file_name=f"Streamline_IPP_Memo_{access_key}.pdf",
                    mime="application/pdf"
                )
        elif status == 0:
            st.error("⛔ Access Deactivated (Status = 0). Your subscription or ticket has expired.")
        else:
            st.warning("⚠️ Invalid Client ID or Ticket Code. Please verify your license key.")
