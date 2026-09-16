"""
Build a Power BI star schema and TMDL semantic model from the screening outputs.

The model outputs are one wide row per precinct, which is fine for a map and
useless for a pivot. This reshapes them into a star so Power BI can slice by
criterion, by year and by scenario without a measure per column:

    DimSite          30 rows   one per precinct, with every categorical attribute
    DimCriterion     14 rows   the criteria, their group, direction and both weights
    DimYear          11 rows   2027-2037, tagged with the tranche window
    DimScenario       2 rows   efficiency / redress
    FactSite         30 rows   yields, areas, distances, ranks
    FactScore       420 rows   site x criterion, the 0-100 normalised score
    FactRanking      60 rows   site x scenario, rank and score
    FactDelivery    330 rows   site x year, units released that year

Outputs
    powerbi/data/*.csv                     the star, for Import mode
    powerbi/CapeTownHousing.SemanticModel/ TMDL model definition + DAX measures
    powerbi/CapeTownHousing.pbip           project file Power BI Desktop opens

Run after suitability_model.py.
"""
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
DATA = PBI / "data"
MODEL = PBI / "CapeTownHousing.SemanticModel"
DEFN = MODEL / "definition"
REPORT = PBI / "CapeTownHousing.Report"

TRANCHE_WINDOW = {"Tranche 1 (2027-2029)": (2027, 2029),
                  "Tranche 2 (2030-2033)": (2030, 2033),
                  "Tranche 3 (2034-2037)": (2034, 2037)}

CRITERION_GROUP = {
    "Job accessibility": "Access", "Transit access": "Access",
    "Social facility access": "Access",
    "Developable land supply": "Capacity", "Land cost": "Capacity",
    "Bulk infrastructure": "Servicing",
    "Flood / water risk": "Constraint", "Terrain buildability": "Constraint",
    "Environmental constraint": "Constraint", "Contamination burden": "Constraint",
    "Heat / green deficit": "Constraint", "Delivery complexity": "Constraint",
    "Spatial redress": "Spatial justice", "Displacement risk": "Spatial justice",
}
MEASURED = {"Transit access", "Social facility access", "Terrain buildability"}
DERIVED = {"Job accessibility", "Developable land supply", "Land cost"}


# ---------------------------------------------------------------- star schema
def build_star():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import suitability_model as M

    rank = pd.read_csv(ROOT / "outputs" / "site_rankings.csv")
    src = pd.read_csv(ROOT / "data" / "candidate_sites.csv")
    crit = pd.read_csv(ROOT / "outputs" / "criteria_scores.csv")
    sens = pd.read_csv(ROOT / "outputs" / "sensitivity.csv")
    isens = pd.read_csv(ROOT / "outputs" / "input_sensitivity.csv")

    zone_class = {
        "GB2": "Business / CBD", "GB5": "Business / CBD", "GB7": "Business / CBD",
        "MU1": "Mixed use", "MU2": "Mixed use",
        "GR1": "Residential", "GR2": "Residential",
        "SR1": "Residential", "SR2": "Residential",
        "GI1": "Industrial - rezoning needed", "GI2": "Industrial - rezoning needed",
        "TR2": "No residential right", "CO1": "No residential right",
        "OS2": "No residential right", "AG": "No residential right",
    }

    dim_site = src[["site_id", "name", "subregion", "typology", "ownership",
                    "zone", "zoning_note", "height_storeys", "asofright_u_ha",
                    "group_area_1950", "lat", "lon"]].copy()
    dim_site["zone_class"] = dim_site.zone.map(zone_class)
    dim_site["tranche"] = dim_site.site_id.map(rank.set_index("site_id").tranche)
    dim_site["publicly_owned"] = dim_site.ownership.str.contains(
        "National|Provincial|City", regex=True)
    dim_site["zoning_blocked"] = dim_site.height_storeys == 0
    dim_site["land_type"] = src.typology.str.split("-").str[0]

    dim_criterion = pd.DataFrame([
        {"criterion": k,
         "criterion_group": CRITERION_GROUP[k],
         "direction": "Benefit" if d > 0 else "Cost",
         "source_column": col,
         "provenance": ("Measured" if k in MEASURED
                        else "Derived" if k in DERIVED else "Estimated"),
         "weight_efficiency": M.SCENARIOS["efficiency"][k],
         "weight_redress": M.SCENARIOS["redress"][k]}
        for k, (col, d) in M.CRITERIA.items()])

    dim_year = pd.DataFrame({"year": range(2027, 2038)})
    dim_year["tranche"] = dim_year.year.map(
        lambda y: next(t for t, (a, b) in TRANCHE_WINDOW.items() if a <= y <= b))
    dim_year["tranche_no"] = dim_year.tranche.str.extract(r"(\d)").astype(int)

    dim_scenario = pd.DataFrame([
        {"scenario": "Efficiency", "scenario_key": "efficiency",
         "description": "Land economics only; blind to Group Areas history."},
        {"scenario": "Redress", "scenario_key": "redress",
         "description": "Adds spatial redress and displacement risk as criteria."}])

    fact_site = (rank[["site_id", "dev_ha", "density_u_ha", "units_total",
                       "units_social", "units_asofright", "units_rezoning",
                       "dist_cbd_km", "dist_bellville_km", "dist_transit_km",
                       "impact_rank", "impact_index", "rank_shift"]]
                 .merge(src[["site_id", "redress_index", "displacement_risk",
                             "social_facility", "slope_pct", "elev_m",
                             "lst_anom_c", "flood_risk", "contamination",
                             "bulk_infra", "enviro_sensitivity",
                             "delivery_complexity", "land_value_r_m2"]],
                        on="site_id")
                 .merge(sens[["site_id", "rank_p05", "rank_p95", "pct_top10"]],
                        on="site_id")
                 .merge(isens[["site_id", "in_rank_p05", "in_rank_p95",
                               "in_pct_top10"]], on="site_id"))

    fact_score = crit.melt(id_vars=["site_id", "name"], var_name="criterion",
                           value_name="score")
    fact_score["criterion"] = fact_score.criterion.str.replace("score::", "", regex=False)
    fact_score = fact_score.drop(columns=["name"])
    fact_score = fact_score[fact_score.criterion.isin(dim_criterion.criterion)]

    fact_ranking = pd.concat([
        rank[["site_id"]].assign(scenario="Efficiency",
                                 rank=rank["rank"], score=rank.suitability),
        rank[["site_id"]].assign(scenario="Redress",
                                 rank=rank.rank_redress, score=rank.suit_redress),
    ], ignore_index=True)

    rows = []
    for r in rank.itertuples():
        a, b = TRANCHE_WINDOW[r.tranche]
        span = b - a + 1
        for y in range(2027, 2038):
            share = 1 / span if a <= y <= b else 0.0
            rows.append({"site_id": r.site_id, "year": y,
                         "units_released": round(r.units_total * share),
                         "under_construction": int(a <= y <= b)})
    fact_delivery = pd.DataFrame(rows)

    return {"DimSite": dim_site, "DimCriterion": dim_criterion,
            "DimYear": dim_year, "DimScenario": dim_scenario,
            "FactSite": fact_site, "FactScore": fact_score,
            "FactRanking": fact_ranking, "FactDelivery": fact_delivery}


# ---------------------------------------------------------------- TMDL
DTYPE = {"int64": "int64", "float64": "double", "bool": "boolean", "object": "string"}


def tmdl_column(name, dtype, fmt=None, hidden=False, summarize=None):
    lines = [f"\tcolumn {name}",
             f"\t\tdataType: {dtype}",
             f"\t\tsourceColumn: {name}"]
    if fmt:
        lines.append(f'\t\tformatString: {fmt}')
    if hidden:
        lines.append("\t\tisHidden")
    if summarize:
        lines.append(f"\t\tsummarizeBy: {summarize}")
    else:
        lines.append("\t\tsummarizeBy: none")
    return "\n".join(lines) + "\n"


def m_partition(table, csv_name):
    """Power Query that reads the CSV sitting next to the .pbip."""
    q = (f'let\n'
         f'    Source = Csv.Document(\n'
         f'        File.Contents(DataFolder & "{csv_name}"),\n'
         f'        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
         f'    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n'
         f'    Typed = Table.TransformColumnTypes(Promoted, {{}}, "en-US")\n'
         f'in\n'
         f'    Typed')
    body = "\n".join("\t\t\t\t" + ln for ln in q.split("\n"))
    return (f"\tpartition {table} = m\n"
            f"\t\tmode: import\n"
            f"\t\tsource =\n{body}\n")


NUMERIC_FORMAT = {
    "units_total": '"#,0"', "units_social": '"#,0"', "units_asofright": '"#,0"',
    "units_rezoning": '"#,0"', "units_released": '"#,0"',
    "dev_ha": '"#,0.0"', "score": '"0.0"', "suitability": '"0.0"',
    "impact_index": '"0.0"', "weight_efficiency": '"0.00"',
    "weight_redress": '"0.00"', "pct_top10": '"0%"', "in_pct_top10": '"0%"',
}
SUMMARIZE_SUM = {"units_total", "units_social", "units_asofright", "units_rezoning",
                 "units_released", "dev_ha"}


def write_tmdl(tables):
    if DEFN.exists():
        shutil.rmtree(DEFN)
    (DEFN / "tables").mkdir(parents=True)

    for name, df in tables.items():
        cols = []
        for c in df.columns:
            dt = DTYPE.get(str(df[c].dtype), "string")
            cols.append(tmdl_column(
                c, dt, NUMERIC_FORMAT.get(c),
                summarize="sum" if c in SUMMARIZE_SUM else None))
        body = (f"table {name}\n\n" + "\n".join(cols) + "\n"
                + tmdl_measures(name)
                + m_partition(name, f"{name}.csv"))
        (DEFN / "tables" / f"{name}.tmdl").write_text(body, encoding="utf-8")

    rels = [
        ("FactSite", "site_id", "DimSite", "site_id"),
        ("FactScore", "site_id", "DimSite", "site_id"),
        ("FactScore", "criterion", "DimCriterion", "criterion"),
        ("FactRanking", "site_id", "DimSite", "site_id"),
        ("FactRanking", "scenario", "DimScenario", "scenario"),
        ("FactDelivery", "site_id", "DimSite", "site_id"),
        ("FactDelivery", "year", "DimYear", "year"),
    ]
    rel_txt = "\n".join(
        f"relationship {f}_{fc}_to_{t}\n"
        f"\tfromColumn: {f}.{fc}\n"
        f"\ttoColumn: {t}.{tc}\n"
        for f, fc, t, tc in rels)
    (DEFN / "relationships.tmdl").write_text(rel_txt, encoding="utf-8")

    (DEFN / "expressions.tmdl").write_text(
        'expression DataFolder = "." meta [IsParameterQuery=true, '
        'Type="Text", IsParameterQueryRequired=true]\n'
        '\tlineageTag: datafolder-param\n\n', encoding="utf-8")

    (DEFN / "model.tmdl").write_text(
        "model Model\n"
        "\tculture: en-ZA\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n\n"
        "annotation PBI_QueryOrder = "
        '["DimSite","DimCriterion","DimYear","DimScenario",'
        '"FactSite","FactScore","FactRanking","FactDelivery"]\n\n',
        encoding="utf-8")

    (DEFN / "database.tmdl").write_text(
        "database\n\tcompatibilityLevel: 1567\n", encoding="utf-8")

    MODEL.mkdir(exist_ok=True)
    (MODEL / "definition.pbism").write_text(json.dumps(
        {"version": "4.0", "settings": {}}, indent=2), encoding="utf-8")


# Measures. Single source of truth: the TMDL model and measures.dax are both
# emitted from this list, so they cannot drift apart. Every expression here was
# accepted by the Analysis Services engine via the Power BI modeling MCP -- the
# DAX is validated, not assumed.
MEASURE_DEFS = [
    # ---- capacity ---------------------------------------------------------
    ("FactSite", "Total Units", "SUM ( FactSite[units_total] )", "#,0", "Capacity",
     "Dwelling units the land could carry at the assumed typology density."),
    ("FactSite", "Social Units", "SUM ( FactSite[units_social] )", "#,0", "Capacity",
     "Units targeted at the sub-R3 500/month band (65% of yield)."),
    ("FactSite", "Developable Ha", "SUM ( FactSite[dev_ha] )", "#,0.0", "Capacity", None),
    ("FactSite", "Site Count", "DISTINCTCOUNT ( FactSite[site_id] )", "#,0", "Capacity", None),
    ("FactSite", "Avg Density", "DIVIDE ( [Total Units], [Developable Ha] )", "#,0",
     "Capacity", "Units per developable hectare."),

    # ---- the zoning constraint, which is the headline ----------------------
    ("FactSite", "Buildable Now", "SUM ( FactSite[units_asofright] )", "#,0", "Zoning",
     "Units possible under current zoning, with no rezoning."),
    ("FactSite", "Needs Rezoning", "SUM ( FactSite[units_rezoning] )", "#,0", "Zoning", None),
    ("FactSite", "% Blocked By Zoning", "DIVIDE ( [Needs Rezoning], [Total Units] )",
     "0.0%", "Zoning", None),
    ("FactSite", "Ha Blocked",
     "CALCULATE ( [Developable Ha], KEEPFILTERS ( DimSite[zoning_blocked] = TRUE ) )",
     "#,0.0", "Zoning", "Hectares whose zone permits no residential use at all."),
    ("FactSite", "Blocked Sites",
     "CALCULATE ( [Site Count], KEEPFILTERS ( DimSite[zoning_blocked] = TRUE ) )",
     "#,0", "Zoning", None),

    # ---- scoring, rebuilt from the criterion grain -------------------------
    ("FactScore", "Avg Score", "AVERAGE ( FactScore[score] )", "0.0", "Scoring",
     "Mean normalised 0-100 criterion score in the current filter context."),
    ("FactScore", "Weighted Score",
     "SUMX ( VALUES ( DimCriterion[criterion] ), [Avg Score] * "
     "CALCULATE ( SELECTEDVALUE ( DimCriterion[weight_efficiency] ) ) )",
     "0.0", "Scoring", "Efficiency-weighted suitability."),
    ("FactScore", "Weighted Score Redress",
     "SUMX ( VALUES ( DimCriterion[criterion] ), [Avg Score] * "
     "CALCULATE ( SELECTEDVALUE ( DimCriterion[weight_redress] ) ) )",
     "0.0", "Scoring", None),

    # ---- the two scenarios and the movement between them -------------------
    ("FactRanking", "Rank Efficiency",
     'CALCULATE ( MIN ( FactRanking[rank] ), DimScenario[scenario] = "Efficiency" )',
     "0", "Scenarios", None),
    ("FactRanking", "Rank Redress",
     'CALCULATE ( MIN ( FactRanking[rank] ), DimScenario[scenario] = "Redress" )',
     "0", "Scenarios", None),
    ("FactRanking", "Rank Shift", "[Rank Redress] - [Rank Efficiency]", "+0;-0;0",
     "Scenarios", "Negative means the site climbs once Group Areas history is priced in."),
    ("FactSite", "Climbs Under Redress",
     "CALCULATE ( [Site Count], KEEPFILTERS ( FactSite[rank_shift] < 0 ) )",
     "#,0", "Scenarios", None),

    # ---- delivery over time ------------------------------------------------
    ("FactDelivery", "Units Released", "SUM ( FactDelivery[units_released] )",
     "#,0", "Delivery", None),
    ("FactDelivery", "Cumulative Units",
     "CALCULATE ( [Units Released], FILTER ( ALL ( DimYear[year] ), "
     "DimYear[year] <= MAX ( DimYear[year] ) ) )", "#,0", "Delivery", None),
    ("FactDelivery", "Pct Of Pipeline Delivered",
     "DIVIDE ( [Cumulative Units], CALCULATE ( [Total Units], ALL ( DimSite ) ) )",
     "0%", "Delivery", None),

    # ---- robustness --------------------------------------------------------
    ("FactSite", "Rank Swing Weights",
     "AVERAGEX ( FactSite, FactSite[rank_p95] - FactSite[rank_p05] )", "0.0",
     "Robustness", "Mean 5th-95th percentile rank interval under weight noise."),
    ("FactSite", "Rank Swing Inputs",
     "AVERAGEX ( FactSite, FactSite[in_rank_p95] - FactSite[in_rank_p05] )", "0.0",
     "Robustness", "Same, under estimate noise. Wider than the weight test."),
    ("FactSite", "Stable Top Ten",
     "CALCULATE ( [Site Count], KEEPFILTERS ( FactSite[pct_top10] >= 0.9 ) )",
     "#,0", "Robustness", None),
]


def tmdl_measures(table):
    out = []
    for tbl, name, expr, fmt, folder, desc in MEASURE_DEFS:
        if tbl != table:
            continue
        block = []
        if desc:
            block.append(f"\t/// {desc}")
        block.append(f"\tmeasure '{name}' = {expr}")
        block.append(f"\t\tformatString: {fmt}")
        block.append(f"\t\tdisplayFolder: {folder}")
        out.append("\n".join(block) + "\n")
    return "\n".join(out)


def measures_dax():
    lines = ["// Cape Town Housing Ground -- DAX measures",
             "// Generated by scripts/build_powerbi_model.py; the TMDL model carries",
             "// the same definitions, so edit the script rather than either output.",
             ""]
    folder = None
    for tbl, name, expr, fmt, fld, desc in MEASURE_DEFS:
        if fld != folder:
            folder = fld
            lines += ["", f"// ---- {folder.lower()} " + "-" * (58 - len(folder))]
        if desc:
            lines.append(f"// {desc}")
        lines.append(f"{name} = {expr}")
    return "\n".join(lines) + "\n"


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    tables = build_star()
    for name, df in tables.items():
        df.to_csv(DATA / f"{name}.csv", index=False)
        print(f"  {name:14} {len(df):>4} rows x {len(df.columns):>2} cols")

    write_tmdl(tables)
    (MODEL / "measures.dax").write_text(measures_dax(), encoding="utf-8")

    REPORT.mkdir(exist_ok=True)
    (REPORT / "definition.pbir").write_text(json.dumps({
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../CapeTownHousing.SemanticModel"}},
    }, indent=2), encoding="utf-8")

    (PBI / "CapeTownHousing.pbip").write_text(json.dumps({
        "version": "1.0",
        "artifacts": [{"report": {"path": "CapeTownHousing.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }, indent=2), encoding="utf-8")

    print(f"\n  {len(MEASURE_DEFS)} measures emitted into the TMDL and measures.dax")
    print(f"\nTMDL   {DEFN}")
    print(f"DAX    {MODEL / 'measures.dax'}")
    print(f"PBIP   {PBI / 'CapeTownHousing.pbip'}")


if __name__ == "__main__":
    main()
