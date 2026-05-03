"""
Core analysis: clean data, compute success metrics, find non-obvious patterns.
Outputs data/processed/companies.csv and data/processed/findings.json
"""

import json
import re
from pathlib import Path
import pandas as pd
import numpy as np
from collections import Counter

Path("data/processed").mkdir(parents=True, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
raw = json.loads(Path("data/raw/yc_companies.json").read_text())
df = pd.DataFrame(raw)
print(f"Loaded {len(df)} companies")

# ── Clean ─────────────────────────────────────────────────────────────────────
# Normalize status
status_map = {
    "active": "active",
    "Acquired": "acquired",
    "acquired": "acquired",
    "Public": "public",
    "public": "public",
    "Inactive": "inactive",
    "inactive": "inactive",
}
df["status"] = df["status"].str.strip().map(status_map).fillna("active")

# Parse batch year and season
def parse_batch(b):
    b = str(b)
    m = re.match(r"(Summer|Winter|Spring|Fall)\s+(\d{4})", b)
    if m:
        return m.group(1), int(m.group(2))
    return "Unknown", None

df[["season", "batch_year"]] = pd.DataFrame(df["batch"].apply(parse_batch).tolist(), index=df.index)
df["batch_year"] = pd.to_numeric(df["batch_year"], errors="coerce")

# Success flag: acquired or public = clear exit
df["exited"] = df["status"].isin(["acquired", "public"])
df["dead"] = df["status"] == "inactive"
df["alive"] = df["status"] == "active"

# Team size cleanup
df["team_size"] = pd.to_numeric(df["team_size"], errors="coerce")

# Industries: flatten list
df["primary_industry"] = df["industries"].apply(
    lambda x: x[0] if isinstance(x, list) and x else "Unknown"
)

# Description length
df["desc_len"] = df["one_liner"].fillna("").str.len()
df["desc_word_count"] = df["one_liner"].fillna("").str.split().str.len()

# Top company flag
df["top_company"] = df["top_company"].fillna(False).astype(bool)

# Region
df["primary_region"] = df["regions"].apply(
    lambda x: x[0] if isinstance(x, list) and x else "Unknown"
)

# ── Keyword signals in description ────────────────────────────────────────────
KEYWORDS = [
    "ai", "machine learning", "ml", "saas", "b2b", "b2c", "enterprise",
    "consumer", "marketplace", "platform", "api", "developer", "fintech",
    "healthcare", "biotech", "climate", "crypto", "blockchain", "automation",
    "no-code", "open source", "vertical", "workflow", "data",
]

for kw in KEYWORDS:
    col = "kw_" + kw.replace(" ", "_").replace("-", "_")
    df[col] = df["one_liner"].fillna("").str.lower().str.contains(
        r"\b" + re.escape(kw) + r"\b", regex=True
    )

# ── Analysis ──────────────────────────────────────────────────────────────────
findings = {}

# 1. Overall exit rates
total = len(df)
exited = df["exited"].sum()
dead = df["dead"].sum()
findings["overall"] = {
    "total": int(total),
    "exited": int(exited),
    "dead": int(dead),
    "alive": int(df["alive"].sum()),
    "exit_rate": round(exited / total * 100, 1),
    "death_rate": round(dead / total * 100, 1),
}
print(f"\nOverall: {exited}/{total} exits ({findings['overall']['exit_rate']}%), "
      f"{dead} dead ({findings['overall']['death_rate']}%)")

# 2. Success by season (Summer vs Winter)
season_stats = df[df["season"].isin(["Summer", "Winter"])].groupby("season").agg(
    count=("exited", "count"),
    exit_rate=("exited", "mean"),
    death_rate=("dead", "mean"),
    top_rate=("top_company", "mean"),
).round(4)
findings["by_season"] = season_stats.to_dict()
print("\n--- By Season ---")
print(season_stats)

# 3. Success by industry
industry_stats = df.groupby("primary_industry").agg(
    count=("exited", "count"),
    exit_rate=("exited", "mean"),
    death_rate=("dead", "mean"),
    top_rate=("top_company", "mean"),
).round(4)
industry_stats = industry_stats[industry_stats["count"] >= 20].sort_values("exit_rate", ascending=False)
findings["by_industry"] = industry_stats.head(20).to_dict()
print("\n--- By Industry (top 10 by exit rate, min 20 companies) ---")
print(industry_stats.head(10))

# 4. Year trend: is success getting harder?
year_stats = df[df["batch_year"].between(2009, 2022)].groupby("batch_year").agg(
    count=("exited", "count"),
    exit_rate=("exited", "mean"),
    death_rate=("dead", "mean"),
).round(4)
findings["by_year"] = year_stats.to_dict()
print("\n--- By Year ---")
print(year_stats)

# 5. Team size sweet spot
df["team_bucket"] = pd.cut(
    df["team_size"],
    bins=[0, 2, 5, 10, 25, 50, 200, 10000],
    labels=["1-2", "3-5", "6-10", "11-25", "26-50", "51-200", "200+"]
)
team_stats = df.groupby("team_bucket", observed=True).agg(
    count=("exited", "count"),
    exit_rate=("exited", "mean"),
    death_rate=("dead", "mean"),
).round(4)
findings["by_team_size"] = team_stats.to_dict()
print("\n--- By Team Size ---")
print(team_stats)

# 6. Description length — does clarity predict success?
df["desc_bucket"] = pd.cut(
    df["desc_word_count"],
    bins=[0, 5, 8, 12, 20, 100],
    labels=["1-5 words", "6-8 words", "9-12 words", "13-20 words", "20+ words"]
)
desc_stats = df.groupby("desc_bucket", observed=True).agg(
    count=("exited", "count"),
    exit_rate=("exited", "mean"),
    death_rate=("dead", "mean"),
).round(4)
findings["by_desc_length"] = desc_stats.to_dict()
print("\n--- By Description Length ---")
print(desc_stats)

# 7. Keyword impact: does "AI" actually help?
kw_results = {}
for kw in KEYWORDS:
    col = "kw_" + kw.replace(" ", "_").replace("-", "_")
    with_kw = df[df[col]]
    without_kw = df[~df[col]]
    if len(with_kw) >= 10:
        kw_results[kw] = {
            "count": int(len(with_kw)),
            "exit_rate_with": round(with_kw["exited"].mean() * 100, 1),
            "exit_rate_without": round(without_kw["exited"].mean() * 100, 1),
            "delta": round((with_kw["exited"].mean() - without_kw["exited"].mean()) * 100, 1),
            "death_rate_with": round(with_kw["dead"].mean() * 100, 1),
        }
findings["by_keyword"] = kw_results
print("\n--- Keyword Impact on Exit Rate ---")
kw_df = pd.DataFrame(kw_results).T.sort_values("delta", ascending=False)
print(kw_df[["count", "exit_rate_with", "exit_rate_without", "delta"]].to_string())

# 8. Geographic breakdown
region_stats = df.groupby("primary_region").agg(
    count=("exited", "count"),
    exit_rate=("exited", "mean"),
    death_rate=("dead", "mean"),
).round(4)
region_stats = region_stats[region_stats["count"] >= 30].sort_values("exit_rate", ascending=False)
findings["by_region"] = region_stats.to_dict()
print("\n--- By Region (min 30 companies) ---")
print(region_stats.head(15))

# 9. "AI" boom: before vs after 2020
ai_col = "kw_ai"
ai_pre = df[(df[ai_col]) & (df["batch_year"] < 2020)]
ai_post = df[(df[ai_col]) & (df["batch_year"] >= 2020)]
findings["ai_era_comparison"] = {
    "pre_2020": {
        "count": int(len(ai_pre)),
        "exit_rate": round(ai_pre["exited"].mean() * 100, 1) if len(ai_pre) else 0,
    },
    "post_2020": {
        "count": int(len(ai_post)),
        "exit_rate": round(ai_post["exited"].mean() * 100, 1) if len(ai_post) else 0,
    },
}
print("\n--- AI mention: pre vs post 2020 ---")
print(json.dumps(findings["ai_era_comparison"], indent=2))

# 10. Top company traits
top = df[df["top_company"]]
print(f"\nTop companies: {len(top)}")
print("Top company industries:")
print(top["primary_industry"].value_counts().head(10))

# ── Save ──────────────────────────────────────────────────────────────────────
df.to_csv("data/processed/companies.csv", index=False)
Path("data/processed/findings.json").write_text(json.dumps(findings, indent=2))
print(f"\nSaved processed CSV and findings to data/processed/")
