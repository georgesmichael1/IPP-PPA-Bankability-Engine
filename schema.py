from pydantic import BaseModel, Field

class IPPAnalysisInput(BaseModel):
    commercial_regime: str = Field(
        default="Solar PV BOO PPA (MENA Single-Buyer)",
        description="Contractual structure (BOO PPA, BESS Tolling SSA, or 24/7 RTC PV+BESS)"
    )
    capacity_mw: float = Field(default=200.0, gt=0, description="Nameplate AC Plant Capacity (MW)")
    bess_capacity_mwh: float = Field(default=0.0, ge=0, description="Installed BESS Storage Capacity (MWh)")
    capex_per_kw: float = Field(default=690.0, gt=0, description="Generation Total Installed Cost ($/kW)")
    bess_capex_per_kwh: float = Field(default=192.0, ge=0, description="BESS Installed Cost ($/kWh)")
    fixed_om_per_kw_yr: float = Field(default=11.5, ge=0, description="Fixed O&M + Insurance ($/kW-year)")
    
    p50_cf_pct: float = Field(default=28.5, gt=0, le=100, description="Base Case P50 Net Capacity Factor (%)")
    p90_1yr_cf_pct: float = Field(default=26.2, gt=0, le=100, description="1-Year P90 Downside Capacity Factor (%)")
    p99_1yr_cf_pct: float = Field(default=23.5, gt=0, le=100, description="1-Year P99 Extreme Capacity Factor (%)")
    annual_degradation_pct: float = Field(default=0.50, ge=0, le=5.0, description="Annual System Output Degradation (%/yr)")
    
    ppa_tariff_usd_mwh: float = Field(default=28.0, gt=0, description="Bid PPA Tariff or Equivalent Revenue ($/MWh)")
    ppa_tenor_years: int = Field(default=25, ge=5, le=35, description="PPA / SSA Concession Tenor (Years)")
    debt_tenor_years: int = Field(default=18, ge=3, le=30, description="Senior Debt Repayment Tenor (Years)")
    
    interest_rate_pct: float = Field(default=6.5, gt=0, le=25.0, description="All-in Senior Debt Interest Rate (%)")
    max_gearing_pct: float = Field(default=80.0, gt=0, le=95.0, description="Maximum Lender Leverage / Gearing Cap (%)")
    target_dscr_p50: float = Field(default=1.35, ge=1.0, le=3.0, description="Target DSCR under P50 Cash Flows (x)")
    target_dscr_p90: float = Field(default=1.20, ge=1.0, le=3.0, description="Minimum DSCR under 1-Yr P90 Cash Flows (x)")
    target_dscr_p99: float = Field(default=1.00, ge=0.8, le=2.5, description="Breakeven DSCR under 1-Yr P99 Cash Flows (x)")
    target_equity_irr_pct: float = Field(default=12.0, gt=0, le=40.0, description="Sponsor Hurdle Equity IRR (%)")
