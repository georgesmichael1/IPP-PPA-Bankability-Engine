import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def generate_waterfall_chart(results: dict, filename: str = "ipp_waterfall.png") -> str:
    years = results["years"]
    cfads_p50 = results["cfads_p50_m"]
    cfads_p90 = results["cfads_p90_m"]
    debt_service = results["debt_service_m"]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(years, cfads_p50, color="#2ca02c", alpha=0.35, label="P50 CFADS (Sponsor Base Case)")
    ax.plot(years, cfads_p90, color="#1f77b4", linewidth=2.2, linestyle="--", label="1-Yr P90 CFADS (Lender Case)")
    ax.bar(years, debt_service, color="#0b3c5d", width=0.55, label="Sculpted Senior Debt Service (P+I)")

    ax.set_title("Concession Cash Flow Waterfall & Sculpted Debt Profile ($M)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Operating Year")
    ax.set_ylabel("USD Millions ($M)")
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8.5)

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

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    bars = ax.bar(labels, values, color=colors, width=0.48)

    ax.set_title("Multi-Criteria Senior Debt Sizing Walls ($M) [Red = Binding Limit]", fontsize=11.5, fontweight="bold")
    ax.set_ylabel("Supportable Senior Debt ($M)")
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    max_v = max(values) if values and max(values) > 0 else 10.0
    ax.set_ylim(0, max_v * 1.22)

    for bar in bars:
        h = bar.get_height()
        ax.annotate(
            f"${h:,.1f}M",
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center", va="bottom", fontsize=9, fontweight="bold"
        )

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    return filename
