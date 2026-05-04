"""
Streamlit dashboard: YC Startup Pattern Analyzer
Run: streamlit run dashboard.py
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="YC Pattern Analyzer",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("data/processed/companies.csv")
    findings = json.loads(Path("data/processed/findings.json").read_text())
    return df, findings

df, findings = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.title("Filters")
years = sorted(df["batch_year"].dropna().unique().astype(int))
year_range = st.sidebar.slider("Batch year range", min(years), max(years), (2010, 2024))
selected_seasons = st.sidebar.multiselect("Season", ["Summer", "Winter", "Spring", "Fall"], default=["Summer", "Winter"])
min_team = st.sidebar.number_input("Min team size", 0, 1000, 0)

mask = (
    df["batch_year"].between(*year_range) &
    df["season"].isin(selected_seasons) &
    (df["team_size"].fillna(0) >= min_team)
)
filtered = df[mask]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🚀 What Actually Makes a YC Startup Succeed?")
st.markdown(
    f"**{len(filtered):,}** companies · {year_range[0]}–{year_range[1]} · "
    f"Live data scraped from YC's public directory"
)

# ── Top-line KPIs ─────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total companies", f"{len(filtered):,}")
k2.metric("Exited (acquired/public)", f"{filtered['exited'].sum():,}",
          f"{filtered['exited'].mean()*100:.1f}%")
k3.metric("Dead / inactive", f"{filtered['dead'].sum():,}",
          f"{filtered['dead'].mean()*100:.1f}%")
k4.metric("Still active", f"{filtered['alive'].sum():,}",
          f"{filtered['alive'].mean()*100:.1f}%")

st.divider()

# ── Finding 1: AI vs ML paradox ───────────────────────────────────────────────
st.header("🔥 Finding #1: 'AI' Is a Red Flag. 'Machine Learning' Isn't.")

col1, col2 = st.columns([1.2, 1])
with col1:
    kw_data = findings["by_keyword"]
    kw_df = pd.DataFrame(kw_data).T.reset_index()
    kw_df.columns = ["keyword", "count", "exit_rate_with", "exit_rate_without", "delta", "death_rate_with"]
    kw_df = kw_df.dropna(subset=["delta"]).sort_values("delta", ascending=True)

    colors = ["#ef4444" if d < 0 else "#22c55e" for d in kw_df["delta"]]
    fig = go.Figure(go.Bar(
        x=kw_df["delta"],
        y=kw_df["keyword"],
        orientation="h",
        marker_color=colors,
        text=[f"{d:+.1f}%" for d in kw_df["delta"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Exit rate delta vs baseline (13.5%) by keyword in description",
        xaxis_title="Exit rate change (percentage points)",
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### The AI Paradox")
    st.markdown("""
Companies that mention **"AI"** in their one-liner have only a **4.2%** exit rate —
vs the **13.5%** baseline. That's a −12 point penalty.

But companies that say **"machine learning"** have a **41.7%** exit rate — +28 points.

**Why?** Two theories:
1. "AI" has become so generic it signals a me-too play
2. "Machine learning" implies technical specificity — founders who know what they're actually building

The post-2020 signal is even more extreme:
    """)
    ai_era = findings["ai_era_comparison"]
    era_df = pd.DataFrame([
        {"Era": "Pre-2020 AI companies", "Exit Rate": ai_era["pre_2020"]["exit_rate"], "n": ai_era["pre_2020"]["count"]},
        {"Era": "Post-2020 AI companies", "Exit Rate": ai_era["post_2020"]["exit_rate"], "n": ai_era["post_2020"]["count"]},
    ])
    fig2 = px.bar(era_df, x="Era", y="Exit Rate", text="Exit Rate",
                  color="Exit Rate", color_continuous_scale="RdYlGn",
                  title="'AI' companies: exit rate collapsed post-2020")
    fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig2.update_layout(height=280, showlegend=False,
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Finding 2: Year trend ─────────────────────────────────────────────────────
st.header("📉 Finding #2: Getting Into YC Used to Mean a ~40% Shot at an Exit")

year_df = pd.DataFrame(findings["by_year"]["exit_rate"], index=["exit_rate"]).T.reset_index()
year_df.columns = ["batch_year", "exit_rate"]
year_df2 = pd.DataFrame(findings["by_year"]["death_rate"], index=["death_rate"]).T.reset_index()
year_df2.columns = ["batch_year", "death_rate"]
year_df2b = pd.DataFrame(findings["by_year"]["count"], index=["count"]).T.reset_index()
year_df2b.columns = ["batch_year", "count"]
year_df = year_df.merge(year_df2, on="batch_year").merge(year_df2b, on="batch_year")
year_df["batch_year"] = year_df["batch_year"].astype(float).astype(int)
year_df["exit_rate_pct"] = year_df["exit_rate"] * 100
year_df["death_rate_pct"] = year_df["death_rate"] * 100

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=year_df["batch_year"], y=year_df["exit_rate_pct"],
    name="Exit rate (acquired/public)", line=dict(color="#22c55e", width=3),
    mode="lines+markers",
))
fig3.add_trace(go.Scatter(
    x=year_df["batch_year"], y=year_df["death_rate_pct"],
    name="Death rate (inactive)", line=dict(color="#ef4444", width=3),
    mode="lines+markers",
))
fig3.add_vline(x=2020, line_dash="dash", line_color="orange",
               annotation_text="COVID / ZIRP era", annotation_position="top left")
fig3.update_layout(
    title="YC exit rate and death rate by batch year (2009–2022)",
    xaxis_title="Batch year",
    yaxis_title="Rate (%)",
    height=380,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig3, use_container_width=True)
st.caption("Note: recent batches (2022+) haven't had enough time to exit — these rates will improve.")

st.divider()

# ── Unicorn Tracker ───────────────────────────────────────────────────────────
st.header("🦄 Unicorn Tracker: 91 Breakout Companies — What Did They Have in Common?")

unicorns = df[df["top_company"] == True].copy()

u1, u2, u3, u4 = st.columns(4)
u1.metric("Total unicorns / top cos", len(unicorns))
u2.metric("Gone public", int((unicorns["status"] == "public").sum()))
u3.metric("Acquired", int((unicorns["status"] == "acquired").sum()))
u4.metric("Still private", int((unicorns["status"] == "active").sum()))

col1, col2 = st.columns(2)

with col1:
    uni_ind = unicorns["primary_industry"].value_counts().reset_index()
    uni_ind.columns = ["industry", "count"]
    fig_u1 = px.bar(
        uni_ind, x="count", y="industry", orientation="h",
        color="count", color_continuous_scale="Oranges",
        title="Unicorn/top company count by industry",
        text="count",
    )
    fig_u1.update_traces(textposition="outside")
    fig_u1.update_layout(
        height=380, showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_u1, use_container_width=True)

with col2:
    uni_year = unicorns[unicorns["batch_year"].between(2007, 2023)].groupby("batch_year").size().reset_index()
    uni_year.columns = ["batch_year", "count"]
    uni_year["batch_year"] = uni_year["batch_year"].astype(float).astype(int)
    fig_u2 = px.bar(
        uni_year, x="batch_year", y="count",
        color="count", color_continuous_scale="Oranges",
        title="Breakout companies produced per batch year",
        labels={"batch_year": "Batch year", "count": "# of top companies"},
        text="count",
    )
    fig_u2.update_traces(textposition="outside")
    fig_u2.update_layout(
        height=380, showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_u2, use_container_width=True)

# Traits comparison: unicorns vs everyone else
st.subheader("Unicorns vs the rest — key differences")
trait_rows = []
for label, mask in [("Unicorns / top cos", unicorns), ("Everyone else", df[~df["top_company"]])]:
    trait_rows.append({
        "Group": label,
        "Avg team size at entry": round(mask["team_size"].median(), 0),
        "% B2B": round((mask["primary_industry"] == "B2B").mean() * 100, 1),
        "% Consumer": round((mask["primary_industry"] == "Consumer").mean() * 100, 1),
        "% Fintech": round((mask["primary_industry"] == "Fintech").mean() * 100, 1),
        "Avg description words": round(mask["desc_word_count"].median(), 1),
    })
st.dataframe(pd.DataFrame(trait_rows).set_index("Group"), use_container_width=True)

# Browseable table
st.subheader("Browse all top companies")
uni_show = unicorns[["name", "batch", "status", "primary_industry", "team_size", "one_liner", "website"]].sort_values("batch")
st.dataframe(uni_show.reset_index(drop=True), use_container_width=True, height=400)

st.divider()

# ── Finding 3: Industry breakdown ─────────────────────────────────────────────
st.header("🏭 Finding #3: Consumer Exits at 17.5%, Healthcare at 8.7%")

col1, col2 = st.columns(2)
with col1:
    ind_data = findings["by_industry"]
    ind_df = pd.DataFrame(ind_data["exit_rate"], index=["exit_rate"]).T.reset_index()
    ind_df.columns = ["industry", "exit_rate"]
    cnt_df = pd.DataFrame(ind_data["count"], index=["count"]).T.reset_index()
    cnt_df.columns = ["industry", "count"]
    death_df = pd.DataFrame(ind_data["death_rate"], index=["death_rate"]).T.reset_index()
    death_df.columns = ["industry", "death_rate"]
    ind_df = ind_df.merge(cnt_df, on="industry").merge(death_df, on="industry")
    ind_df["exit_pct"] = (ind_df["exit_rate"] * 100).round(1)
    ind_df["death_pct"] = (ind_df["death_rate"] * 100).round(1)
    ind_df = ind_df.sort_values("exit_pct", ascending=True)

    fig4 = go.Figure(go.Bar(
        x=ind_df["exit_pct"], y=ind_df["industry"],
        orientation="h",
        marker_color="#3b82f6",
        text=[f"{v:.1f}%" for v in ind_df["exit_pct"]],
        textposition="outside",
    ))
    fig4.update_layout(
        title="Exit rate by industry",
        xaxis_title="Exit rate (%)",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig4, use_container_width=True)

with col2:
    fig5 = px.scatter(
        ind_df, x="exit_pct", y="death_pct", size="count",
        text="industry", color="exit_pct",
        color_continuous_scale="RdYlGn",
        title="Exit rate vs death rate by industry (bubble = company count)",
        labels={"exit_pct": "Exit rate (%)", "death_pct": "Death rate (%)"},
    )
    fig5.update_traces(textposition="top center")
    fig5.update_layout(
        height=400,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ── Finding 4: Team size ──────────────────────────────────────────────────────
st.header("👥 Finding #4: The Bigger You Are at YC Entry, The Better You Do")

team_data = findings["by_team_size"]
team_df = pd.DataFrame(team_data["exit_rate"], index=["exit_rate"]).T.reset_index()
team_df.columns = ["team_bucket", "exit_rate"]
team_df2 = pd.DataFrame(team_data["death_rate"], index=["death_rate"]).T.reset_index()
team_df2.columns = ["team_bucket", "death_rate"]
team_cnt = pd.DataFrame(team_data["count"], index=["count"]).T.reset_index()
team_cnt.columns = ["team_bucket", "count"]
team_df = team_df.merge(team_df2, on="team_bucket").merge(team_cnt, on="team_bucket")
team_df["exit_pct"] = (team_df["exit_rate"] * 100).round(1)
team_df["death_pct"] = (team_df["death_rate"] * 100).round(1)

fig6 = make_subplots(specs=[[{"secondary_y": True}]])
fig6.add_trace(go.Bar(
    x=team_df["team_bucket"], y=team_df["exit_pct"],
    name="Exit rate", marker_color="#22c55e",
), secondary_y=False)
fig6.add_trace(go.Scatter(
    x=team_df["team_bucket"], y=team_df["death_pct"],
    name="Death rate", line=dict(color="#ef4444", width=3),
    mode="lines+markers",
), secondary_y=True)
fig6.update_layout(
    title="Team size at YC entry vs exit & death rates",
    height=380,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
fig6.update_yaxes(title_text="Exit rate (%)", secondary_y=False)
fig6.update_yaxes(title_text="Death rate (%)", secondary_y=True)
st.plotly_chart(fig6, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Solo/duo founders exit rate", "10.4%", "-3.1 pts vs avg")
col2.metric("11–25 person teams exit rate", "18.8%", "+5.3 pts vs avg")
col3.metric("200+ person teams exit rate", "26.0%", "+12.5 pts vs avg")
st.caption("Solo/duo founders have a 31% death rate — highest of any group")

st.divider()

# ── Finding 5: Geography ──────────────────────────────────────────────────────
st.header("🌍 Finding #5: Canada Quietly Outperforms the United States")

region_data = findings["by_region"]
reg_df = pd.DataFrame(region_data["exit_rate"], index=["exit_rate"]).T.reset_index()
reg_df.columns = ["region", "exit_rate"]
reg_cnt = pd.DataFrame(region_data["count"], index=["count"]).T.reset_index()
reg_cnt.columns = ["region", "count"]
reg_death = pd.DataFrame(region_data["death_rate"], index=["death_rate"]).T.reset_index()
reg_death.columns = ["region", "death_rate"]
reg_df = reg_df.merge(reg_cnt, on="region").merge(reg_death, on="region")
reg_df["exit_pct"] = (reg_df["exit_rate"] * 100).round(1)
reg_df = reg_df[reg_df["region"] != "Unspecified"].sort_values("exit_pct", ascending=False)

fig7 = px.bar(
    reg_df, x="region", y="exit_pct",
    color="exit_pct", color_continuous_scale="Blues",
    text="exit_pct",
    title="Exit rate by founder region",
    labels={"exit_pct": "Exit rate (%)", "region": "Region"},
)
fig7.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig7.update_layout(
    height=400,
    showlegend=False,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig7, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.info("🇨🇦 **Canada** leads at 17.5% exit rate — higher than the USA (16.3%)")
with col2:
    st.warning("📡 **Remote-first** companies have a low 6.3% exit rate but also only 5.3% death rate — they just keep existing")

st.divider()

# ── Explorer ──────────────────────────────────────────────────────────────────
st.header("🔎 Company Explorer")
col1, col2 = st.columns([1, 3])
with col1:
    status_filter = st.selectbox("Status", ["All", "exited", "active", "dead"])
    industry_filter = st.selectbox("Industry", ["All"] + sorted(df["primary_industry"].dropna().unique().tolist()))
with col2:
    search = st.text_input("Search company name or description")

exp = filtered.copy()
if status_filter != "All":
    if status_filter == "exited":
        exp = exp[exp["exited"]]
    elif status_filter == "active":
        exp = exp[exp["alive"]]
    elif status_filter == "dead":
        exp = exp[exp["dead"]]
if industry_filter != "All":
    exp = exp[exp["primary_industry"] == industry_filter]
if search:
    mask2 = (
        exp["name"].fillna("").str.lower().str.contains(search.lower()) |
        exp["one_liner"].fillna("").str.lower().str.contains(search.lower())
    )
    exp = exp[mask2]

show_cols = ["name", "batch", "status", "primary_industry", "team_size", "one_liner", "website"]
st.dataframe(
    exp[show_cols].head(200).reset_index(drop=True),
    use_container_width=True,
    height=400,
)
st.caption(f"Showing {min(200, len(exp))} of {len(exp)} matching companies")

st.divider()
st.markdown(
    "*Data source: YC public company directory via Algolia. · "
    "Made by [Shayan Awan](https://www.linkedin.com/in/shayan-awan)*"
)
