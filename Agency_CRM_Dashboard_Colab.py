# ============================================================
#  Digital Agency CRM & Project Delivery Analytics Dashboard
#  Single-cell Google Colab Script — Bug-Free, Production Ready
# ============================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from google.colab import files

# ── Reproducibility ──────────────────────────────────────────
np.random.seed(42)

# ════════════════════════════════════════════════════════════
#  STEP 1 — GENERATE REALISTIC CRM DATA
# ════════════════════════════════════════════════════════════

N = 2500
date_range = pd.date_range(start="2024-01-01", end="2025-12-31", freq="D")

platforms       = ["WordPress", "Salla", "Custom Development"]
account_managers = ["AM - Team A", "AM - Team B", "AM - Team C"]
phases          = [
    "1. Contracting",
    "2. UI/UX Design",
    "3. Development",
    "4. Client Review",
    "5. Launch",
]

# --- Platform distribution (Salla smaller share, Custom rarer) ---
platform_col = np.random.choice(
    platforms,
    size=N,
    p=[0.45, 0.35, 0.20],
)

# --- Expected Days by platform ---
expected_days_col = np.where(
    platform_col == "Salla",
    np.random.randint(5, 11, N),
    np.where(
        platform_col == "WordPress",
        np.random.randint(15, 31, N),
        np.random.randint(40, 61, N),
    ),
)

# --- Phase column (uniform distribution across phases) ---
phase_col = np.random.choice(phases, size=N)

# --- Actual Days with phase-specific delay logic ---
actual_days_col = np.empty(N, dtype=int)
delay_reason_col = np.empty(N, dtype=object)

for i in range(N):
    phase   = phase_col[i]
    exp     = expected_days_col[i]
    plat    = platform_col[i]

    if phase == "4. Client Review":
        # Massive delays — 40-110 % over budget
        multiplier = np.random.uniform(1.40, 2.10)
        actual = max(exp + 1, int(exp * multiplier))
        delay_reason_col[i] = np.random.choice(
            ["Client Feedback Pending", "Scope Creep"],
            p=[0.85, 0.15],
        )

    elif phase == "2. UI/UX Design":
        # Second biggest bottleneck — 20-70 % overrun
        multiplier = np.random.uniform(1.20, 1.70)
        actual = max(exp + 1, int(exp * multiplier))
        delay_reason_col[i] = np.random.choice(
            ["Design Revisions", "Client Feedback Pending"],
            p=[0.75, 0.25],
        )

    elif phase == "3. Development":
        # Moderate delays — 0-40 % overrun
        on_time_prob = 0.35
        if np.random.rand() < on_time_prob:
            actual = np.random.randint(max(1, exp - 3), exp + 1)
            delay_reason_col[i] = "On Time"
        else:
            multiplier = np.random.uniform(1.05, 1.40)
            actual = max(exp + 1, int(exp * multiplier))
            delay_reason_col[i] = np.random.choice(
                ["Technical Bugs", "Scope Creep"],
                p=[0.70, 0.30],
            )

    elif phase == "1. Contracting":
        # Usually on time or small delays
        on_time_prob = 0.60
        if np.random.rand() < on_time_prob:
            actual = np.random.randint(max(1, exp - 2), exp + 1)
            delay_reason_col[i] = "On Time"
        else:
            multiplier = np.random.uniform(1.05, 1.25)
            actual = max(exp + 1, int(exp * multiplier))
            delay_reason_col[i] = "Scope Creep"

    else:  # 5. Launch — mostly on time
        on_time_prob = 0.75
        if np.random.rand() < on_time_prob:
            actual = np.random.randint(max(1, exp - 2), exp + 1)
            delay_reason_col[i] = "On Time"
        else:
            multiplier = np.random.uniform(1.05, 1.20)
            actual = max(exp + 1, int(exp * multiplier))
            delay_reason_col[i] = "Technical Bugs"

    actual_days_col[i] = int(actual)

# --- Enforce: 'On Time' ONLY when Actual <= Expected ---
mask_wrong_on_time = (delay_reason_col == "On Time") & (actual_days_col > expected_days_col)
actual_days_col[mask_wrong_on_time] = expected_days_col[mask_wrong_on_time]

mask_delayed_no_reason = (actual_days_col > expected_days_col) & (delay_reason_col == "On Time")
fallback_reasons = np.random.choice(
    ["Technical Bugs", "Scope Creep", "Client Feedback Pending"],
    size=mask_delayed_no_reason.sum(),
)
delay_reason_col[mask_delayed_no_reason] = fallback_reasons

# --- Assemble DataFrame ---
df = pd.DataFrame(
    {
        "Project_ID":       [f"PRJ-{str(i+1).zfill(4)}" for i in range(N)],
        "Start_Date":       np.random.choice(date_range, size=N),
        "Platform":         platform_col,
        "Account_Manager":  np.random.choice(account_managers, size=N),
        "Project_Phase":    phase_col,
        "Expected_Days":    expected_days_col,
        "Actual_Days":      actual_days_col,
        "Delay_Reason":     delay_reason_col,
    }
)

print(f"✅ Dataset generated: {len(df):,} rows × {len(df.columns)} columns")
print(df.dtypes)
print("\nDelay Reason distribution:")
print(df["Delay_Reason"].value_counts())

# ════════════════════════════════════════════════════════════
#  STEP 2 — CALCULATE KPIs
# ════════════════════════════════════════════════════════════

# KPI 1 — Total Projects Delivered (unique Project IDs)
total_projects = df["Project_ID"].nunique()

# KPI 2 — Average Lead Time (sum of Actual_Days per project → average)
lead_time_per_project = df.groupby("Project_ID")["Actual_Days"].sum()
avg_lead_time = lead_time_per_project.mean()

# KPI 3 — On-Time Delivery Rate (phase level)
on_time_rate = (df["Actual_Days"] <= df["Expected_Days"]).mean() * 100

print(f"\n📊 KPIs Calculated")
print(f"  Total Projects Delivered : {total_projects:,}")
print(f"  Average Lead Time        : {avg_lead_time:.1f} days")
print(f"  On-Time Delivery Rate    : {on_time_rate:.1f}%")

# ════════════════════════════════════════════════════════════
#  STEP 3 — BUILD 3 INDEPENDENT PLOTLY FIGURES
# ════════════════════════════════════════════════════════════

# ── Palette ───────────────────────────────────────────────────
INDIGO      = "#4F46E5"   # Primary
VIOLET      = "#7C3AED"   # Secondary
CORAL       = "#F43F5E"   # Delays / alerts
INDIGO_LIGHT = "#818CF8"
BG          = "#f8fafc"
CARD_BG     = "#ffffff"
TEXT_DARK   = "#1e293b"
TEXT_MUTED  = "#64748b"

CHART_FONT = dict(family="'DM Sans', 'Segoe UI', sans-serif", color=TEXT_DARK)
BASE_LAYOUT = dict(
    paper_bgcolor=CARD_BG,
    plot_bgcolor=CARD_BG,
    font=CHART_FONT,
    margin=dict(t=55, b=45, l=50, r=25),
    hoverlabel=dict(
        bgcolor="white",
        font_size=13,
        font_family="'DM Sans', sans-serif",
    ),
)

# ── Figure 1 — Bottleneck Clustered Bar ───────────────────────
phase_agg = (
    df.groupby("Project_Phase")[["Expected_Days", "Actual_Days"]]
    .mean()
    .reset_index()
    .sort_values("Project_Phase")
)

fig_bottleneck = go.Figure()

fig_bottleneck.add_trace(
    go.Bar(
        name="Avg Expected Days",
        x=phase_agg["Project_Phase"],
        y=phase_agg["Expected_Days"].round(1),
        marker_color=INDIGO,
        marker_line_width=0,
        opacity=0.88,
        hovertemplate="<b>%{x}</b><br>Expected: %{y:.1f} days<extra></extra>",
    )
)

fig_bottleneck.add_trace(
    go.Bar(
        name="Avg Actual Days",
        x=phase_agg["Project_Phase"],
        y=phase_agg["Actual_Days"].round(1),
        marker_color=CORAL,
        marker_line_width=0,
        opacity=0.88,
        hovertemplate="<b>%{x}</b><br>Actual: %{y:.1f} days<extra></extra>",
    )
)

fig_bottleneck.update_layout(
    **BASE_LAYOUT,
    title=dict(
        text="Phase Bottleneck Analysis — Expected vs Actual Days",
        font=dict(size=16, color=TEXT_DARK),
        x=0.02,
    ),
    barmode="group",
    bargap=0.25,
    bargroupgap=0.08,
    legend=dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=1.08,
        font=dict(size=12),
    ),
    xaxis=dict(
        tickfont=dict(size=11),
        showgrid=False,
        zeroline=False,
    ),
    yaxis=dict(
        title="Days",
        tickfont=dict(size=11),
        gridcolor="#e2e8f0",
        zeroline=False,
    ),
)

# ── Figure 2 — Platform Lead Time Horizontal Bar ─────────────
platform_lead = (
    df.groupby(["Project_ID", "Platform"])["Actual_Days"]
    .sum()
    .reset_index()
    .groupby("Platform")["Actual_Days"]
    .mean()
    .reset_index()
    .sort_values("Actual_Days", ascending=True)
)

bar_colors = [INDIGO_LIGHT, INDIGO, VIOLET]

fig_platform = go.Figure()

fig_platform.add_trace(
    go.Bar(
        orientation="h",
        x=platform_lead["Actual_Days"].round(1),
        y=platform_lead["Platform"],
        marker_color=bar_colors[: len(platform_lead)],
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>Avg Lead Time: %{x:.1f} days<extra></extra>",
        text=platform_lead["Actual_Days"].round(1),
        textposition="outside",
        textfont=dict(size=12, color=TEXT_DARK),
    )
)

fig_platform.update_layout(
    **BASE_LAYOUT,
    title=dict(
        text="Average Lead Time by Platform",
        font=dict(size=16, color=TEXT_DARK),
        x=0.02,
    ),
    xaxis=dict(
        title="Total Actual Days",
        tickfont=dict(size=11),
        gridcolor="#e2e8f0",
        zeroline=False,
    ),
    yaxis=dict(
        tickfont=dict(size=12),
        showgrid=False,
    ),
    showlegend=False,
)

# ── Figure 3 — Delay Reason Donut ────────────────────────────
delay_dist = (
    df[df["Delay_Reason"] != "On Time"]["Delay_Reason"]
    .value_counts()
    .reset_index()
)
delay_dist.columns = ["Delay_Reason", "Count"]

DONUT_COLORS = [CORAL, VIOLET, INDIGO, INDIGO_LIGHT, "#FDA4AF"]

fig_delay = go.Figure()

fig_delay.add_trace(
    go.Pie(
        labels=delay_dist["Delay_Reason"],
        values=delay_dist["Count"],
        hole=0.5,
        marker=dict(
            colors=DONUT_COLORS[: len(delay_dist)],
            line=dict(color="white", width=2),
        ),
        textinfo="label+percent",
        textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        pull=[0.03] * len(delay_dist),
    )
)

fig_delay.update_layout(
    **BASE_LAYOUT,
    title=dict(
        text="Delay Root Cause Distribution",
        font=dict(size=16, color=TEXT_DARK),
        x=0.02,
    ),
    legend=dict(
        orientation="v",
        x=1.02,
        y=0.5,
        font=dict(size=11),
    ),
    annotations=[
        dict(
            text="<b>Delays</b>",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=CORAL),
            xanchor="center",
        )
    ],
)

print("✅ All 3 Plotly figures created successfully.")

# ════════════════════════════════════════════════════════════
#  STEP 4 — BUILD PURE HTML/CSS DASHBOARD
# ════════════════════════════════════════════════════════════

# Convert figures — no Plotly.js bundle embedded (loaded via CDN)
html_bottleneck = fig_bottleneck.to_html(full_html=False, include_plotlyjs=False)
html_platform   = fig_platform.to_html(full_html=False, include_plotlyjs=False)
html_delay      = fig_delay.to_html(full_html=False, include_plotlyjs=False)

# KPI color-coding for on-time rate
if on_time_rate >= 75:
    otr_color, otr_badge = "#16a34a", "#dcfce7"   # green
elif on_time_rate >= 50:
    otr_color, otr_badge = "#d97706", "#fef3c7"   # amber
else:
    otr_color, otr_badge = "#dc2626", "#fee2e2"   # red

html_dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Digital Agency CRM &amp; Project Delivery Analytics</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:         #f8fafc;
      --card:       #ffffff;
      --indigo:     #4F46E5;
      --violet:     #7C3AED;
      --coral:      #F43F5E;
      --text-dark:  #1e293b;
      --text-muted: #64748b;
      --border:     #e2e8f0;
      --shadow:     0 1px 3px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.06);
      --radius:     14px;
    }}

    body {{
      background: var(--bg);
      font-family: 'DM Sans', 'Segoe UI', sans-serif;
      color: var(--text-dark);
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, var(--indigo) 0%, var(--violet) 100%);
      padding: 28px 40px 26px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 4px 24px rgba(79,70,229,.25);
    }}
    header h1 {{
      color: #ffffff;
      font-size: 1.45rem;
      font-weight: 700;
      letter-spacing: -0.3px;
    }}
    header p {{
      color: rgba(255,255,255,.75);
      font-size: .875rem;
      margin-top: 3px;
    }}
    .header-badge {{
      background: rgba(255,255,255,.18);
      color: #fff;
      font-size: .78rem;
      font-weight: 600;
      letter-spacing: .5px;
      padding: 6px 14px;
      border-radius: 20px;
      border: 1px solid rgba(255,255,255,.3);
    }}

    /* ── Main layout ── */
    main {{
      padding: 32px 40px 48px;
      display: grid;
      row-gap: 28px;
    }}

    /* ── KPI row ── */
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}

    .kpi-card {{
      background: var(--card);
      border-radius: var(--radius);
      padding: 24px 28px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      position: relative;
      overflow: hidden;
      transition: transform .18s ease, box-shadow .18s ease;
    }}
    .kpi-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 28px rgba(0,0,0,.10);
    }}
    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: var(--accent-bar, var(--indigo));
      border-radius: var(--radius) var(--radius) 0 0;
    }}
    .kpi-label {{
      font-size: .775rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .8px;
      color: var(--text-muted);
      margin-bottom: 10px;
    }}
    .kpi-value {{
      font-size: 2.4rem;
      font-weight: 700;
      letter-spacing: -1px;
      line-height: 1;
      color: var(--text-dark);
    }}
    .kpi-value span {{
      font-size: 1.1rem;
      font-weight: 500;
      color: var(--text-muted);
      margin-left: 3px;
    }}
    .kpi-sub {{
      font-size: .8rem;
      color: var(--text-muted);
      margin-top: 8px;
    }}
    .kpi-badge {{
      display: inline-block;
      font-size: .78rem;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 20px;
      margin-top: 9px;
      background: {otr_badge};
      color: {otr_color};
    }}

    /* ── Chart cards ── */
    .chart-card {{
      background: var(--card);
      border-radius: var(--radius);
      padding: 20px 20px 12px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
    }}
    .chart-card .chart-title {{
      font-size: .8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .7px;
      color: var(--text-muted);
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 4px;
    }}

    .chart-full {{ grid-column: 1 / -1; }}

    .bottom-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}

    /* ── Responsive ── */
    @media (max-width: 900px) {{
      main {{ padding: 20px; }}
      .kpi-row {{ grid-template-columns: 1fr; }}
      .bottom-row {{ grid-template-columns: 1fr; }}
      header {{ flex-direction: column; gap: 12px; text-align: center; }}
    }}
  </style>
</head>
<body>

<header>
  <div>
    <h1>🚀 Digital Agency — CRM &amp; Project Delivery Analytics</h1>
    <p>Data range: Jan 2024 – Dec 2025 &nbsp;·&nbsp; {N:,} phase records &nbsp;·&nbsp; {total_projects:,} unique projects</p>
  </div>
  <div class="header-badge">OPERATIONS DASHBOARD</div>
</header>

<main>

  <!-- KPI Cards -->
  <div class="kpi-row">

    <div class="kpi-card" style="--accent-bar: #4F46E5;">
      <div class="kpi-label">Total Projects Delivered</div>
      <div class="kpi-value">{total_projects:,}</div>
      <div class="kpi-sub">Unique project IDs tracked</div>
    </div>

    <div class="kpi-card" style="--accent-bar: #7C3AED;">
      <div class="kpi-label">Average Lead Time</div>
      <div class="kpi-value">{avg_lead_time:.0f}<span>days</span></div>
      <div class="kpi-sub">Contracting → Launch (actual)</div>
    </div>

    <div class="kpi-card" style="--accent-bar: {otr_color};">
      <div class="kpi-label">On-Time Delivery Rate</div>
      <div class="kpi-value" style="color:{otr_color}">{on_time_rate:.1f}<span>%</span></div>
      <div class="kpi-badge">{'✅ On Track' if on_time_rate >= 75 else '⚠️ Needs Attention' if on_time_rate >= 50 else '🔴 Critical'}</div>
    </div>

  </div>

  <!-- Bottleneck Chart — Full Width -->
  <div class="chart-card chart-full">
    <div class="chart-title">📊 Phase Bottleneck — Expected vs Actual Days</div>
    {html_bottleneck}
  </div>

  <!-- Bottom Row: Platform + Delay Donut -->
  <div class="bottom-row">

    <div class="chart-card">
      <div class="chart-title">⏱ Lead Time by Platform</div>
      {html_platform}
    </div>

    <div class="chart-card">
      <div class="chart-title">🔍 Delay Root Cause Breakdown</div>
      {html_delay}
    </div>

  </div>

</main>

</body>
</html>"""

print("✅ HTML dashboard string assembled successfully.")

# ════════════════════════════════════════════════════════════
#  STEP 5 — EXPORT & AUTO-DOWNLOAD
# ════════════════════════════════════════════════════════════

output_filename = "Agency_CRM_Analytics_Dashboard.html"

with open(output_filename, "w", encoding="utf-8") as f:
    f.write(html_dashboard)

print(f"\n✅ Dashboard saved → {output_filename}")
print(f"   File size: {len(html_dashboard)/1024:.1f} KB")
print("\n⬇️  Triggering download...")

files.download(output_filename)

print("\n🎉 Done! Your dashboard is downloading.")
