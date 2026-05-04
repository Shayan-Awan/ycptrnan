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
    page_icon=None,
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
st.title("What Actually Makes a YC Startup Succeed?")
st.markdown(
    f"**{len(filtered):,}** companies · {year_range[0]}–{year_range[1]} · "
    f"Live data scraped from YC's public directory"
)
st.markdown("""
Y Combinator has funded nearly 6,000 companies since 2005. Everyone knows the famous ones — Stripe, Airbnb, Dropbox —
but what about the other 5,700? We scraped the full public YC directory and ran the numbers to find what actually
separates the winners from the rest. Not what the blog posts say. Not survivorship-biased founder advice.
The raw data, across every batch, every industry, every team size.

Five findings stood out — some confirmed intuitions, others were genuinely surprising.
""")

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
st.header("Finding #1: 'AI' Is a Red Flag. 'Machine Learning' Isn't.")

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

st.markdown("""
**Takeaway:** The language founders use to describe their company is a surprisingly strong signal. "AI" has become
so overused that it now reads as noise — investors and the market have seen thousands of AI pitches and most go nowhere.
"Machine learning," by contrast, implies a founder who understands what they're actually building at a technical level.
The same pattern holds for "workflow" (−8 pts) and "healthcare" (−9.7 pts) — categories where the problem is clear
but the path to a liquidity event is genuinely harder. If you're writing your one-liner, be specific. Generic positioning
is a quiet killer.
""")

st.divider()

# ── Finding 2: Year trend ─────────────────────────────────────────────────────
st.header("Finding #2: Getting Into YC Used to Mean a ~40% Shot at an Exit")

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

st.markdown("""
**Takeaway:** The 2010 and 2011 cohorts were extraordinary — over 40–50% of those companies went on to exit.
That era had less competition, cheaper capital, and a market that hadn't yet saturated with YC alumni. By 2018,
the exit rate had dropped to ~18%, and by 2022 it sits at 7.4%. Part of this is simply time — a 2022 company
hasn't had long enough to exit yet. But the trend is real regardless: the field is more crowded, the bar to
stand out is higher, and the funding environment post-2021 is dramatically different. Getting into YC today
is a different game than it was a decade ago.
""")

st.divider()

# ── Unicorn Tracker ───────────────────────────────────────────────────────────
st.header("Unicorn Tracker: 91 Breakout Companies — What Did They Have in Common?")

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

st.markdown("""
**Takeaway:** B2B dominates the breakout list — 45 of 91 top companies are B2B, with Consumer and Fintech a
distant second and third. But what's more interesting is what's missing: Healthcare has 6 top companies despite
being the third-largest industry by company count. The path from YC-funded healthcare startup to major exit is
long and hard — regulatory timelines, clinical validation, and reimbursement cycles don't fit neatly into the
standard VC return window. Meanwhile, the 2012–2014 era was the golden age for producing breakout companies:
Coinbase, Instacart, Stripe, DoorDash, Zapier, Gusto, Flexport, Cruise, and GitLab all came out of those three years.
""")

st.divider()

# ── Finding 3: Industry breakdown ─────────────────────────────────────────────
st.header("Finding #3: Consumer Exits at 17.5%, Healthcare at 8.7%")

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

st.markdown("""
**Takeaway:** Consumer is the boom-or-bust category. It has the highest exit rate (17.5%) but also the highest
death rate (35.4%) — nearly 1 in 3 consumer YC companies ends up inactive. B2B is the safe bet: lower ceiling
but also a dramatically lower death rate (14.7%), which makes sense given the stickier revenue, longer contracts,
and more predictable sales cycles. Healthcare's low exit rate isn't necessarily a quality signal — many of those
companies are still alive and building, just on longer timelines than the data can yet capture.
""")

st.divider()

# ── Finding 4: Team size ──────────────────────────────────────────────────────
st.header("Finding #4: The Bigger You Are at YC Entry, The Better You Do")

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

st.markdown("""
**Takeaway:** This one cuts against the YC mythology of the scrappy two-person team. Companies that show up
to YC with 11+ people exit at nearly double the rate of solo founders. The most likely explanation: larger teams
signal more validation. A founder who's convinced 10+ people to quit their jobs and join them before YC is
a different type of operator than someone with a side project. That said, the solo/duo path isn't dead —
it just comes with a 31% failure rate, and the ones that make it tend to be outliers. The data doesn't say
don't start alone. It says know what you're signing up for.
""")

st.divider()

# ── Finding 5: Geography ──────────────────────────────────────────────────────
st.header("Finding #5: Canada Quietly Outperforms the United States")

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
    st.info("**Canada** leads at 17.5% exit rate — higher than the USA (16.3%)")
with col2:
    st.warning("**Remote-first** companies have a low 6.3% exit rate but also only 5.3% death rate — they just keep existing")

st.markdown("""
**Takeaway:** Canada punches above its weight. With only 137 companies vs 3,889 from the US, Canadian founders
outperform on exit rate. One possible reason: Canadian founders who make it to YC tend to be further along —
they've had less access to early-stage capital at home, so by the time they apply they've built more. The remote
finding is intriguing in a different way: remote-first companies almost never die, but they also rarely break out.
They become sustainable, quiet businesses — which might be exactly what their founders wanted, but it doesn't
show up as an exit in this dataset.
""")

st.divider()

# ── Key Takeaways ─────────────────────────────────────────────────────────────
st.header("Key Takeaways")
st.markdown("""
After looking at 5,868 companies across 20 years of YC batches, here's what the data actually says:

**1. Language is a signal, not just packaging.**
The words in your one-liner correlate with real outcomes. "AI" has become a liability. Specificity — "machine learning," "SaaS," "developer tools" — is associated with higher exits. Founders who know exactly what they're building tend to describe it exactly.

**2. The game has gotten harder.**
A 2010 YC company had a ~50% shot at an exit. A 2022 company sits at 7.4% — and even accounting for the time needed to mature, the trend is real. More companies in each batch, more competition post-YC, and a tighter funding market all contribute.

**3. Consumer is high risk, high reward. B2B is the baseline.**
Consumer companies exit more often but die far more often too. B2B is more predictable — slower to break out, but far less likely to go to zero. If you're optimizing for survival odds, B2B is the safer path. If you want a shot at something massive, Consumer can get you there faster.

**4. Team size matters more than the mythology suggests.**
YC is famous for funding two-person teams, and those stories dominate the narrative. But the data shows that larger teams at entry have dramatically better outcomes. Validation before YC — in the form of people willing to join you — is a strong predictor of success.

**5. Where you're from matters less than you think, but not zero.**
The US dominates by volume, but Canada outperforms by rate. The most likely explanation isn't geography — it's selection effects. Founders who clear higher local bars before reaching YC tend to be further along when they get there.
""")

st.divider()

# ── Explorer ──────────────────────────────────────────────────────────────────
st.header("Company Explorer")
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

# ── Success Predictor ─────────────────────────────────────────────────────────
st.header("Success Predictor: How Would Your Startup Score?")
st.markdown("Enter your startup's details and see how you'd stack up against 5,868 YC companies.")

with st.form("predictor_form"):
    p1, p2 = st.columns(2)
    with p1:
        p_industry = st.selectbox("Industry", sorted(df["primary_industry"].dropna().unique().tolist()))
        p_team = st.number_input("Team size", min_value=1, max_value=10000, value=3)
        p_region = st.selectbox("Region", sorted(df["primary_region"].dropna().unique().tolist()))
    with p2:
        p_season = st.selectbox("YC batch season", ["Summer", "Winter", "Spring", "Fall"])
        p_oneliner = st.text_input("Your one-liner", placeholder="e.g. Stripe for Southeast Asia")

    submitted = st.form_submit_button("Score my startup", use_container_width=True)

if submitted and p_oneliner:
    BASELINE = 13.5

    scores = {}

    # Industry score
    ind_exits = df.groupby("primary_industry")["exited"].mean() * 100
    ind_score = ind_exits.get(p_industry, BASELINE)
    scores["Industry"] = (ind_score, BASELINE, f"{p_industry} cohort exits at {ind_score:.1f}%")

    # Team size score
    def team_exit(size):
        mask = pd.cut(
            pd.Series([size]),
            bins=[0, 2, 5, 10, 25, 50, 200, 10000],
            labels=["1-2","3-5","6-10","11-25","26-50","51-200","200+"]
        )
        bucket = mask.iloc[0]
        sub = df[df["team_bucket"] == bucket]
        return sub["exited"].mean() * 100 if len(sub) else BASELINE

    t_score = team_exit(p_team)
    scores["Team size"] = (t_score, BASELINE, f"Team of {p_team} — this bucket exits at {t_score:.1f}%")

    # Region score
    reg_exits = df.groupby("primary_region")["exited"].mean() * 100
    reg_score = reg_exits.get(p_region, BASELINE)
    scores["Region"] = (reg_score, BASELINE, f"{p_region} founders exit at {reg_score:.1f}%")

    # Season score
    season_exits = df[df["season"].isin(["Summer","Winter"])].groupby("season")["exited"].mean() * 100
    s_score = season_exits.get(p_season, BASELINE)
    scores["Batch season"] = (s_score, BASELINE, f"{p_season} batches exit at {s_score:.1f}%")

    # Keyword score
    import re as _re
    KEYWORDS = {
        "ai": -12.1, "machine learning": 28.2, "saas": 10.4,
        "no-code": 13.8, "workflow": -8.0, "healthcare": -9.7,
        "b2b": -5.9, "crypto": -4.0, "blockchain": -4.0,
        "open source": 7.7, "developer": 7.5, "marketplace": 4.7,
        "platform": 3.0, "api": 5.0, "fintech": 13.8,
    }
    ol_lower = p_oneliner.lower()
    kw_hits = [(kw, delta) for kw, delta in KEYWORDS.items() if _re.search(r"\b" + _re.escape(kw) + r"\b", ol_lower)]
    kw_delta = sum(d for _, d in kw_hits)
    kw_score = BASELINE + kw_delta
    if kw_hits:
        kw_note = "Keywords found: " + ", ".join(f"{kw} ({d:+.0f})" for kw, d in kw_hits)
    else:
        kw_note = "No strong keywords detected — neutral signal"
    scores["Description keywords"] = (kw_score, BASELINE, kw_note)

    # Final score = weighted average of factor scores
    weights = {"Industry": 0.30, "Team size": 0.25, "Region": 0.15, "Batch season": 0.10, "Description keywords": 0.20}
    final = sum(scores[k][0] * weights[k] for k in scores)
    final = max(1.0, min(final, 60.0))

    # Display
    st.subheader(f"Your score: **{final:.1f}%** predicted exit probability")

    color = "#22c55e" if final >= BASELINE else "#ef4444"
    delta_label = f"{final - BASELINE:+.1f} pts vs YC average"

    gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=final,
        delta={"reference": BASELINE, "suffix": "%"},
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 55]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 10], "color": "#fecaca"},
                {"range": [10, 20], "color": "#fef9c3"},
                {"range": [20, 55], "color": "#dcfce7"},
            ],
            "threshold": {"line": {"color": "gray", "width": 2}, "thickness": 0.75, "value": BASELINE},
        },
        title={"text": "Exit probability vs 13.5% YC baseline"},
    ))
    gauge.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(gauge, use_container_width=True)

    # Factor breakdown
    st.subheader("Factor breakdown")
    for factor, (score, base, note) in scores.items():
        delta = score - base
        icon = "▲" if delta > 0 else ("▼" if delta < 0 else "●")
        color_tag = "green" if delta > 0 else ("red" if delta < 0 else "gray")
        st.markdown(f"**{factor}** — :{color_tag}[{icon} {delta:+.1f} pts]  \n_{note}_")

    # Similar companies
    st.subheader("Most similar YC companies to you")
    sim = df[df["primary_industry"] == p_industry].copy()
    sim["team_diff"] = (sim["team_size"] - p_team).abs()
    sim = sim.sort_values(["top_company", "team_diff"], ascending=[False, True])
    show_sim = ["name", "batch", "status", "team_size", "one_liner", "website"]
    st.dataframe(sim[show_sim].head(10).reset_index(drop=True), use_container_width=True)

elif submitted and not p_oneliner:
    st.warning("Enter a one-liner to get your score.")

st.divider()
st.markdown(
    "*Data source: YC public company directory via Algolia. · "
    "Made by [Shayan Awan](https://www.linkedin.com/in/shayan-awan)*"
)
