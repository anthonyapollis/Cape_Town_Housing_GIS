"""
Cape Town Low-Income Housing Site Suitability Model
===================================================
Multi-criteria decision analysis (MCDA) over 30 candidate precincts.

Method
------
1. Derive gravity-based job accessibility from real coordinates + metro employment nodes.
2. Normalise every criterion to 0-100 (benefit criteria ascending, cost criteria inverted).
3. Weighted linear combination using AHP-derived weights.
4. Estimate deliverable yield (units) by typology density.
5. Assign a 4D delivery tranche (2027-2037) from readiness + complexity.
6. Monte Carlo sensitivity analysis on weights to test rank stability.

Provenance note: the remote-sensing columns (ndvi, ndbi, lst_anom_c, impervious_pct)
and the qualitative 0-100 columns in candidate_sites.csv are DESKTOP ESTIMATES.
Run scripts/gee_remote_sensing.js to replace the RS columns with measured values.
"""
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(42)

# --------------------------------------------------------------------------
# 1. Employment nodes (lat, lon, formal-job weight ~ thousands of jobs)
# --------------------------------------------------------------------------
JOB_NODES = [
    ("Cape Town CBD",      -33.9249, 18.4241, 240),
    ("Bellville CBD",      -33.9006, 18.6292, 130),
    ("Century City",       -33.8920, 18.5100,  75),
    ("Epping Industria",   -33.9330, 18.5450,  60),
    ("Airport Industria",  -33.9690, 18.6010,  55),
    ("Montague Gardens",   -33.8690, 18.5230,  45),
    ("Claremont",          -34.0250, 18.4650,  40),
    ("Somerset West",      -34.0800, 18.8500,  35),
]


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def job_accessibility(lat, lon, beta=1.6):
    """Gravity accessibility index: sum(Jobs / (d+1)^beta)."""
    return sum(w / (haversine(lat, lon, jl, jo) + 1.0) ** beta
               for _, jl, jo, w in JOB_NODES)


# --------------------------------------------------------------------------
# 2. Criteria:  label -> (source column, direction, AHP weight)
#    direction: +1 = more is better (benefit), -1 = more is worse (cost)
# --------------------------------------------------------------------------
CRITERIA = {
    "Job accessibility":        ("job_access_idx",      +1),
    "Transit access":           ("dist_transit_km",     -1),
    "Developable land supply":  ("dev_ha",              +1),
    "Land cost":                ("land_value_r_m2",     -1),
    "Bulk infrastructure":      ("bulk_infra",          +1),
    "Flood / water risk":       ("flood_risk",          -1),
    "Terrain buildability":     ("slope_pct",           -1),
    "Environmental constraint": ("enviro_sensitivity",  -1),
    "Contamination burden":     ("contamination",       -1),
    "Social facility access":   ("social_facility",     +1),
    "Heat / green deficit":     ("lst_anom_c",          -1),
    "Delivery complexity":      ("delivery_complexity", -1),
    "Spatial redress":          ("redress_index",       +1),
    "Displacement risk":        ("displacement_risk",   -1),
}

# --------------------------------------------------------------------------
# 3. Two weighting scenarios. Which one is "correct" is a political choice,
#    not a technical one, so the model runs both and reports the movement.
#
#    EFFICIENCY treats the problem as land economics: put housing where it is
#    cheapest to serve and closest to work. It is deliberately blind to who was
#    removed from where, and so it tends to reproduce the existing geography.
#
#    REDRESS adds the Group Areas history as an explicit criterion. Spatial
#    redress is high where a site puts low-income households back inside the
#    well-located, job-rich land reserved for white occupation under the Group
#    Areas Act; it is low where a site adds yet more density to the peripheral
#    townships apartheid built. Displacement risk is its counterweight: an
#    inner-city site can advance redress on paper while evicting the working-
#    class -- overwhelmingly coloured -- community already living there.
# --------------------------------------------------------------------------
SCENARIOS = {
    "efficiency": {
        "Job accessibility": 0.18, "Transit access": 0.16,
        "Developable land supply": 0.10, "Land cost": 0.08,
        "Bulk infrastructure": 0.10, "Flood / water risk": 0.07,
        "Terrain buildability": 0.04, "Environmental constraint": 0.06,
        "Contamination burden": 0.05, "Social facility access": 0.06,
        "Heat / green deficit": 0.03, "Delivery complexity": 0.07,
        "Spatial redress": 0.0, "Displacement risk": 0.0,
    },
    "redress": {
        "Job accessibility": 0.14, "Transit access": 0.13,
        "Developable land supply": 0.08, "Land cost": 0.04,
        "Bulk infrastructure": 0.08, "Flood / water risk": 0.06,
        "Terrain buildability": 0.03, "Environmental constraint": 0.05,
        "Contamination burden": 0.04, "Social facility access": 0.05,
        "Heat / green deficit": 0.02, "Delivery complexity": 0.05,
        "Spatial redress": 0.17, "Displacement risk": 0.06,
    },
}
for nm, w in SCENARIOS.items():
    assert set(w) == set(CRITERIA), nm
    assert abs(sum(w.values()) - 1.0) < 1e-9, (nm, sum(w.values()))

# Density assumptions (dwelling units per developable hectare) by typology
DENSITY = {
    "Adaptive-Reuse":         260,
    "Infill":                 220,
    "Brownfield-Infill":      200,
    "Brownfield-Rail":        190,
    "Brownfield-Strategic":   140,
    "Brownfield-Industrial":  150,
    "Brownfield-Delivered":   160,
    "Restitution":            130,
    "Infill-Upgrading":       110,
    "Corridor-Infill":        140,
    "Corridor-Greenfield":     90,
    "Greenfield-Infill":       85,
    "Greenfield-Sensitive":    70,
    "Greenfield-Contested":    70,
    "Greenfield-Periphery":    65,
    "Greenfield-Constrained":  60,
}
# Share of units targeted at the sub-R3 500/month income band
SOCIAL_SHARE = 0.65


def minmax(series, direction):
    """Scale to 0-100; invert if the criterion is a cost."""
    lo, hi = series.min(), series.max()
    if math.isclose(hi, lo):
        return pd.Series(50.0, index=series.index)
    s = (series - lo) / (hi - lo)
    return (s if direction > 0 else 1 - s) * 100.0


def build(df):
    df = df.copy()
    df["job_access_idx"] = [job_accessibility(r.lat, r.lon) for r in df.itertuples()]
    df["dist_cbd_km"] = [round(haversine(r.lat, r.lon, -33.9249, 18.4241), 2)
                         for r in df.itertuples()]
    df["dist_bellville_km"] = [round(haversine(r.lat, r.lon, -33.9006, 18.6292), 2)
                               for r in df.itertuples()]
    # log-compress land value so the Atlantic Seaboard does not dominate the axis
    df["land_value_r_m2"] = np.log10(df["land_value_r_m2"])

    for label, (col, direction) in CRITERIA.items():
        df["score::" + label] = minmax(df[col], direction)

    smat = df[["score::" + k for k in CRITERIA]].to_numpy()
    for name, wmap in SCENARIOS.items():
        w = np.array([wmap[k] for k in CRITERIA])
        df["suit_" + name] = (smat * w).sum(axis=1)
        df["rank_" + name] = df["suit_" + name].rank(ascending=False, method="min").astype(int)
    df["suitability"] = df["suit_efficiency"]
    df["rank"] = df["rank_efficiency"]
    # Negative = the site climbs once the Group Areas history is priced in.
    df["rank_shift"] = df["rank_redress"] - df["rank_efficiency"]

    df["density_u_ha"] = df["typology"].map(DENSITY)
    df["units_total"] = (df["dev_ha"] * df["density_u_ha"]).round().astype(int)
    df["units_social"] = (df["units_total"] * SOCIAL_SHARE).round().astype(int)

    # Zoning reality check. units_total is what the land could physically carry;
    # what you may build TODAY is capped by the current zone's height right.
    # The gap is the rezoning workload, and it is most of the programme.
    df["units_asofright"] = (df["dev_ha"] *
                             df[["density_u_ha", "asofright_u_ha"]].min(axis=1)).round().astype(int)
    df["units_rezoning"] = df["units_total"] - df["units_asofright"]
    df["rezoning_pct"] = (df["units_rezoning"] / df["units_total"] * 100).round(1)

    # Suitability alone rewards small, perfectly-located infill parcels. The
    # portfolio question is different: how much housing does a good site deliver?
    # Impact = site quality x log-scaled yield, renormalised to 0-100.
    raw = df["suitability"] * np.log10(df["units_total"].clip(lower=10))
    df["impact_index"] = minmax(raw, +1)
    df["impact_rank"] = df["impact_index"].rank(ascending=False, method="min").astype(int)
    weights = np.array([SCENARIOS["efficiency"][k] for k in CRITERIA])
    return df, smat, weights


def tranche(row):
    """4D phasing: readiness is complexity + servicing + tenure clarity."""
    readiness = ((100 - row["delivery_complexity"]) * 0.5
                 + row["bulk_infra"] * 0.3
                 + (100 - row["contamination"]) * 0.2)
    if readiness >= 62 and row["rank"] <= 12:
        return "Tranche 1 (2027-2029)"
    if readiness >= 48:
        return "Tranche 2 (2030-2033)"
    return "Tranche 3 (2034-2037)"


# Columns still carrying an analyst estimate after measure_site_context.py has
# replaced transit distance, facility access, elevation and slope with measurements.
# Criteria whose source column is still an analyst estimate after
# measure_site_context.py has replaced transit distance, facility access,
# elevation and slope with measurements. NDVI/NDBI/impervious are estimates too
# but feed no criterion -- they are reported, not scored -- so perturbing them
# could not move a rank and they are left out.
ESTIMATED_CRITERIA = [
    "Bulk infrastructure", "Flood / water risk", "Environmental constraint",
    "Contamination burden", "Heat / green deficit", "Delivery complexity",
    "Spatial redress", "Displacement risk",
]


def _rank_desc(scores):
    """Competition rank (1 = best) along each row of a 2-D score array."""
    order = np.argsort(-scores, axis=1, kind="stable")
    ranks = np.empty_like(order)
    np.put_along_axis(ranks, order,
                      np.tile(np.arange(1, scores.shape[1] + 1), (scores.shape[0], 1)),
                      axis=1)
    return ranks


def input_sensitivity(df, n=2000, noise=0.15):
    """Perturb the ESTIMATES, not the weights.

    Weight sensitivity asks "what if we valued these things differently". This
    asks the more uncomfortable question: the inputs are desktop judgements, so
    what if they are simply wrong? Every still-estimated column is jittered by
    +/-15% of its own range and the ranking recomputed.

    Only the affected criteria are re-normalised -- the measured and derived
    columns cannot move, so re-running the whole model per draw would be 2 000
    times the work for the same answer.
    """
    labels = list(CRITERIA)
    smat = df[["score::" + k for k in labels]].to_numpy()          # (30, 14)
    w = np.array([SCENARIOS["efficiency"][k] for k in labels])
    base_rank = df["rank_efficiency"].to_numpy()

    draws = np.tile(smat, (n, 1, 1))                                # (n, 30, 14)
    for label in ESTIMATED_CRITERIA:
        col, direction = CRITERIA[label]
        v = df[col].to_numpy(float)
        lo, hi = v.min(), v.max()
        span = (hi - lo) * noise
        pert = np.clip(v + rng.uniform(-span, span, (n, v.size)), lo, hi)
        mn = pert.min(axis=1, keepdims=True)
        rng_ = np.where((mx := pert.max(axis=1, keepdims=True)) - mn == 0,
                        1.0, mx - mn)
        sc = (pert - mn) / rng_
        if direction < 0:
            sc = 1.0 - sc
        draws[:, :, labels.index(label)] = sc * 100.0

    scores = (draws * w).sum(axis=2)                                # (n, 30)
    ranks = _rank_desc(scores)

    return pd.DataFrame({
        "site_id": df["site_id"].to_numpy(),
        "name": df["name"].to_numpy(),
        "rank_base": base_rank,
        "in_rank_mean": ranks.mean(axis=0).round(2),
        "in_rank_p05": np.percentile(ranks, 5, axis=0),
        "in_rank_p95": np.percentile(ranks, 95, axis=0),
        "in_pct_top10": (ranks <= 10).mean(axis=0).round(3),
    })


def sensitivity(df, smat, weights, n=5000, jitter=0.30):
    """Perturb weights +/- 30 percent (renormalised) and record rank stability."""
    ranks = np.zeros((n, len(df)))
    for i in range(n):
        w = weights * rng.uniform(1 - jitter, 1 + jitter, size=weights.shape)
        w = w / w.sum()
        sc = (smat * w).sum(axis=1)
        ranks[i] = pd.Series(sc).rank(ascending=False, method="min").to_numpy()
    return pd.DataFrame({
        "site_id": df["site_id"].to_numpy(),
        "name": df["name"].to_numpy(),
        "rank_base": df["rank"].to_numpy(),
        "rank_mean": ranks.mean(axis=0).round(2),
        "rank_p05": np.percentile(ranks, 5, axis=0),
        "rank_p95": np.percentile(ranks, 95, axis=0),
        "pct_top10": (ranks <= 10).mean(axis=0).round(3),
    })


def to_geojson(df, path):
    feats = []
    for r in df.itertuples():
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
            "properties": {
                "site_id": r.site_id, "name": r.name, "subregion": r.subregion,
                "rank": int(r.rank), "suitability": round(r.suitability, 2),
                "dev_ha": r.dev_ha, "typology": r.typology, "ownership": r.ownership,
                "rank_redress": int(r.rank_redress), "rank_shift": int(r.rank_shift),
                "group_area_1950": r.group_area_1950, "redress_index": r.redress_index,
                "displacement_risk": r.displacement_risk,
                "impact_rank": int(r.impact_rank), "impact_index": round(r.impact_index, 2),
                "units_total": int(r.units_total), "units_social": int(r.units_social),
                "zone": r.zone, "height_storeys": int(r.height_storeys),
                "asofright_u_ha": int(r.asofright_u_ha),
                "units_asofright": int(r.units_asofright),
                "units_rezoning": int(r.units_rezoning), "zoning_note": r.zoning_note,
                "dist_cbd_km": r.dist_cbd_km, "dist_transit_km": r.dist_transit_km,
                "ndvi": r.ndvi, "ndbi": r.ndbi, "lst_anom_c": r.lst_anom_c,
                "impervious_pct": r.impervious_pct, "tranche": r.tranche,
            },
        })
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, indent=1))


def zoning_by_redress(df):
    """How the rezoning burden splits across the spatial-redress gradient.

    The per-site correlation is weak; the aggregate is not. What matters is
    where the UNITS sit, and they sit on land that needs rezoning precisely
    where redress value is highest.
    """
    band = np.where(df.redress_index >= 70, "High redress",
           np.where(df.redress_index >= 40, "Mid redress", "Low redress"))
    g = df.assign(band=band).groupby("band").agg(
        sites=("site_id", "count"), ha=("dev_ha", "sum"),
        units=("units_total", "sum"), buildable_now=("units_asofright", "sum"),
        needs_rezoning=("units_rezoning", "sum"))
    g["pct_blocked"] = (g.needs_rezoning / g.units * 100).round(1)
    return {b: g.loc[b].to_dict() for b in
            ["High redress", "Mid redress", "Low redress"] if b in g.index}


def main():
    src = pd.read_csv(ROOT / "data" / "candidate_sites.csv")
    df, smat, weights = build(src)
    df["tranche"] = df.apply(tranche, axis=1)
    df = df.sort_values("rank")

    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    cols = ["rank", "site_id", "name", "subregion", "typology", "ownership",
            "suitability", "rank_redress", "suit_redress", "rank_shift",
            "impact_rank", "impact_index", "dev_ha", "density_u_ha",
            "units_total", "units_social", "zone", "height_storeys",
            "asofright_u_ha", "units_asofright", "units_rezoning",
            "dist_cbd_km", "dist_bellville_km", "dist_transit_km", "tranche"]
    df[cols].round(2).to_csv(out / "site_rankings.csv", index=False)
    df[["site_id", "name"] + ["score::" + k for k in CRITERIA]].round(1).to_csv(
        out / "criteria_scores.csv", index=False)
    sens = sensitivity(df, df[["score::" + k for k in CRITERIA]].to_numpy(), weights)
    sens.sort_values("rank_base").to_csv(out / "sensitivity.csv", index=False)
    isens = input_sensitivity(df)
    isens.sort_values("rank_base").to_csv(out / "input_sensitivity.csv", index=False)
    to_geojson(df, out / "candidate_sites.geojson")

    summary = {
        "sites_screened": int(len(df)),
        "total_developable_ha": float(df["dev_ha"].sum()),
        "total_units_potential": int(df["units_total"].sum()),
        "social_units_potential": int(df["units_social"].sum()),
        "units_asofright": int(df["units_asofright"].sum()),
        "units_rezoning": int(df["units_rezoning"].sum()),
        "ha_blocked_by_zoning": float(df.loc[df.height_storeys == 0, "dev_ha"].sum()),
        "sites_blocked_by_zoning": int((df.height_storeys == 0).sum()),
        "zoning_by_redress": zoning_by_redress(df),
        "blocked_sites": df.loc[df.height_storeys == 0,
            ["name", "zone", "dev_ha", "units_total", "redress_index", "ownership"]]
            .sort_values("units_total", ascending=False).to_dict("records"),
        "top10_units": int(df.nsmallest(10, "rank")["units_total"].sum()),
        "tranche_units": df.groupby("tranche")["units_total"].sum().to_dict(),
        "job_nodes": [{"name": n, "lat": la, "lon": lo, "jobs_k": w}
                      for n, la, lo, w in JOB_NODES],
        "scenarios": SCENARIOS,
        "weights": SCENARIOS["efficiency"],
        "stable_top10": sens[sens.pct_top10 >= 0.90]["name"].tolist(),
        "stable_top10_inputs": isens[isens.in_pct_top10 >= 0.90]["name"].tolist(),
        "input_rank_swing_mean": float((isens.in_rank_p95 - isens.in_rank_p05).mean().round(2)),
        "biggest_climb_on_redress": df.nsmallest(6, "rank_shift")[["name", "rank_shift"]]
            .set_index("name")["rank_shift"].to_dict(),
        "biggest_fall_on_redress": df.nlargest(6, "rank_shift")[["name", "rank_shift"]]
            .set_index("name")["rank_shift"].to_dict(),
        "top10_by_impact": df.nsmallest(10, "impact_rank")[["name", "units_total"]]
            .set_index("name")["units_total"].to_dict(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    pd.set_option("display.width", 220)
    print(df[cols].round(1).head(15).to_string(index=False))
    print("\nSensitivity (rank stability, 5000 weight draws):")
    print(sens.sort_values("rank_base").head(15).to_string(index=False))
    print("\nSummary:\n", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
