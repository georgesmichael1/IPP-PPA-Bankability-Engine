import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def generate_waterfall_chart(results: dict, filename: str = "ipp_waterfall.png") -> str:
    years = results["years"]
    cfads_p50 = results["cfads_p50_m"]
    cfads_p90 = results["cfads_p90_m"]
    principal = results["principal_series_m"]
    interest = results["interest_series_m"]

    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.bar(years, cfads_p50, color="#2ca02c", alpha=0.28, label="P50 CFADS (Sponsor Base Case)")
    ax.bar(years, interest, color="#1f77b4", width=0.55, label="Senior Debt Interest")
    ax.bar(years, principal, bottom=interest, color="#0b3c5d", width=0.55, label="Sculpted Principal Repayment")
    ax.plot(years, cfads_p90, color="#d62728", linewidth=2.0, linestyle="--", label="1-Yr P90 CFADS (Lender Sizing)")

    ax.set_title("Concession Cash Flow Waterfall & Sculpted P+I Debt Profile ($M)", fontsize=11.5, fontweight="bold")
    ax.set_xlabel("Operating Year")
    ax.set_ylabel("USD Millions ($M)")
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    return filename

def generate_debt_sizing_chart(results: dict, filename: str = "ipp_debt_sizing.png") -> str:
    constraints = results["debt_by_constraint_m"]
    labels = list(constraints.keys())
    values = list(constraints.values())
    binding = results["binding_constraint"]

    colors = ["#d62728" if k == binding else "#4a7c59" for k in labels]

    fig, ax = plt.subplots(figsize=(7.8, 3.5))
    bars = ax.bar(labels, values, color=colors, width=0.45)

    ax.set_title("Multi-Criteria Senior Debt Sizing Walls ($M) [Red = Binding Wall]", fontsize=11.5, fontweight="bold")
    ax.set_ylabel("Supportable Senior Debt ($M)")
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    max_v = max(values) if values and max(values) > 0 else 10.0
    ax.set_ylim(0, max_v * 1.22)

    for bar in bars:
        h = bar.get_height()
        ax.annotate(
            f"${h:,.1f}M",
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom", fontsize=8.5, fontweight="bold"
        )

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    return filename

def generate_stress_dscr_chart(results: dict, filename: str = "ipp_stress_dscr.png") -> str:
    d_years = results["debt_years"]
    dscr_50 = results["dscr_p50_series"]
    dscr_90 = results["dscr_p90_series"]
    dscr_stress = results["dscr_stress_series"]

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.plot(d_years, dscr_50, color="#2ca02c", marker="o", markersize=3.5, linewidth=2.0, label="P50 Base Case DSCR")
    ax.plot(d_years, dscr_90, color="#1f77b4", linewidth=2.0, linestyle="--", label="1-Yr P90 Sculpted Target DSCR")
    ax.plot(d_years, dscr_stress, color="#d62728", marker="s", markersize=3.5, linewidth=2.0, label="S&P / Fitch Downside Stress DSCR")
    ax.axhline(1.10, color="#ff7f0e", linestyle=":", linewidth=1.5, label="Dividend Lock-Up Covenant (1.10x)")
    ax.axhline(1.00, color="#000000", linestyle="-.", linewidth=1.5, label="Lender Breakeven Floor (1.00x)")

    ax.set_title("Credit Rating Agency Downside Stress Test: DSCR Trajectory Over Debt Tenor", fontsize=11, fontweight="bold")
    ax.set_xlabel("Debt Repayment Year")
    ax.set_ylabel("DSCR Coverage Multiple (x)")
    ax.set_ylim(0.6, max(dscr_50 + [1.8]) * 1.15)
    ax.grid(axis="both", linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", fontsize=7.8, ncol=2)

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    return filename

def generate_termination_and_bess_chart(results: dict, filename: str = "ipp_term_bess.png") -> str:
    years = results["years"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.6))

    # Left Subplot: 25-Year Open Solar Contracts / GSA Termination Buyout Curves
    ax1.plot(years, results["buyout_offtaker_curve"], color="#2ca02c", linewidth=2.2, label="Offtaker Default (Put Option)")
    ax1.plot(years, results["buyout_fm_curve"], color="#ff7f0e", linewidth=1.8, linestyle="--", label="Natural Force Majeure")
    ax1.plot(years, results["buyout_project_curve"], color="#d62728", linewidth=2.0, label="Project Default (Call Option)")
    ax1.set_title("GSA / PPA Termination Buyout Exposure ($M)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Concession Year")
    ax1.set_ylabel("Buyout Valuation ($M)")
    ax1.grid(axis="both", linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=7.5)

    # Right Subplot: BESS 3-Ledger Degradation & Year-8 Augmentation vs. Tariff Sensitivity
    if results["bess_capex_m"] > 0:
        ax2.plot(years, results["bess_retention_aug"], color="#0b3c5d", linewidth=2.2, label="Yr-8 Phased Augmentation (MWh %)")
        ax2.plot(years, results["bess_retention_overbuild"], color="#1f77b4", linestyle="--", linewidth=1.8, label="Yr-0 Overbuild Trajectory (MWh %)")
        ax2.plot(years, results["bess_rte_series"], color="#d62728", linestyle=":", linewidth=1.8, label="Degrading Round-Trip Eff. (RTE %)")
        ax2.set_title("BESS 3-Ledger Energy Retention & RTE Decay", fontsize=10, fontweight="bold")
        ax2.set_xlabel("Operating Year")
        ax2.set_ylabel("Capability / Efficiency (%)")
        ax2.grid(axis="both", linestyle="--", alpha=0.5)
        ax2.legend(loc="lower left", fontsize=7.5)
    else:
        bars = ax2.bar(results["tariff_sens_labels"], results["tariff_sens_irrs"], color="#1f77b4", width=0.45)
        ax2.set_title("Sponsor Equity IRR Sensitivity to PPA Tariff", fontsize=10, fontweight="bold")
        ax2.set_ylabel("Equity IRR (%)")
        ax2.grid(axis="y", linestyle="--", alpha=0.5)
        for bar in bars:
            h = bar.get_height()
            ax2.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 2),
                         textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    return filename
