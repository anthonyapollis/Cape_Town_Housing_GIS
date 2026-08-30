"""
Invariants for the screening model and its outputs.

These are the things that must stay true no matter how the criteria, weights or
site list change. Run after any edit to the model or the data:

    python -m pytest tests/ -q          # or: python tests/test_model.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import suitability_model as M  # noqa: E402

SITES = pd.read_csv(ROOT / "data" / "candidate_sites.csv")
RANK = pd.read_csv(ROOT / "outputs" / "site_rankings.csv")
SUMMARY = json.loads((ROOT / "outputs" / "summary.json").read_text())
N = len(SITES)


# ---------------------------------------------------------------- source data
def test_no_missing_values():
    assert not SITES.isna().any().any(), SITES.columns[SITES.isna().any()].tolist()


def test_site_ids_unique_and_named():
    assert SITES.site_id.is_unique and SITES.name.is_unique
    assert (SITES.name.str.strip() != "").all()


def test_coordinates_inside_the_metro():
    assert SITES.lat.between(-34.4, -33.4).all()
    assert SITES.lon.between(18.2, 19.1).all()


def test_scored_ranges_are_sane():
    for col in ["flood_risk", "enviro_sensitivity", "contamination", "bulk_infra",
                "social_facility", "delivery_complexity", "redress_index",
                "displacement_risk"]:
        assert SITES[col].between(0, 100).all(), col
    assert (SITES.dev_ha > 0).all()
    assert SITES.slope_pct.between(0, 60).all()
    assert (SITES.dist_transit_km >= 0).all()


def test_every_typology_has_a_density():
    assert set(SITES.typology) <= set(M.DENSITY)


def test_every_zone_maps_to_a_storey_limit():
    assert SITES.height_storeys.between(0, 20).all()
    # a zone that permits no residential must yield nothing as of right
    blocked = SITES[SITES.height_storeys == 0]
    assert (blocked.asofright_u_ha == 0).all()


# ---------------------------------------------------------------- weights
def test_scenario_weights_are_complete_and_normalised():
    for name, w in M.SCENARIOS.items():
        assert set(w) == set(M.CRITERIA), name
        assert math.isclose(sum(w.values()), 1.0, abs_tol=1e-9), name


def test_efficiency_scenario_ignores_the_justice_criteria():
    """The whole point of the pair: one weighting is deliberately blind to it."""
    eff = M.SCENARIOS["efficiency"]
    assert eff["Spatial redress"] == 0 and eff["Displacement risk"] == 0
    assert M.SCENARIOS["redress"]["Spatial redress"] > 0


# ---------------------------------------------------------------- scoring
def test_normalisation_bounds_and_direction():
    s = pd.Series([1.0, 5.0, 10.0])
    up = M.minmax(s, +1)
    down = M.minmax(s, -1)
    assert up.min() == 0 and up.max() == 100
    assert down.iloc[0] == 100 and down.iloc[-1] == 0      # cost criteria invert
    flat = M.minmax(pd.Series([3.0, 3.0, 3.0]), +1)
    assert (flat == 50).all()                              # no divide-by-zero


def test_job_accessibility_falls_with_distance():
    near = M.job_accessibility(-33.9249, 18.4241)          # the CBD itself
    far = M.job_accessibility(-34.36, 18.30)               # the far south-west
    assert near > far * 5


def test_haversine_against_a_known_pair():
    # Cape Town CBD to Bellville CBD is about 19 km
    d = M.haversine(-33.9249, 18.4241, -33.9006, 18.6292)
    assert 18 < d < 20


# ---------------------------------------------------------------- outputs
def test_rankings_are_complete_permutations():
    for col in ["rank", "rank_redress", "impact_rank"]:
        assert sorted(RANK[col]) == list(range(1, N + 1)), col


def test_rank_shift_is_the_difference_between_scenarios():
    assert (RANK.rank_redress - RANK["rank"] == RANK.rank_shift).all()


def test_yield_identity_holds():
    assert (RANK.units_asofright + RANK.units_rezoning == RANK.units_total).all()
    assert (RANK.units_asofright <= RANK.units_total).all()
    assert (RANK.units_total == (RANK.dev_ha * RANK.density_u_ha).round()).all()


def test_social_share_is_applied():
    assert ((RANK.units_social / RANK.units_total - M.SOCIAL_SHARE).abs() < 0.01).all()


def test_as_of_right_respects_the_zoning_cap():
    cap = (RANK.dev_ha * RANK[["density_u_ha", "asofright_u_ha"]].min(axis=1)).round()
    assert (RANK.units_asofright == cap).all()


def test_tranche_labels_are_known():
    assert set(RANK.tranche) <= {"Tranche 1 (2027-2029)", "Tranche 2 (2030-2033)",
                                 "Tranche 3 (2034-2037)"}


def test_summary_totals_match_the_rows():
    assert SUMMARY["sites_screened"] == N
    assert SUMMARY["total_units_potential"] == int(RANK.units_total.sum())
    assert SUMMARY["units_asofright"] == int(RANK.units_asofright.sum())
    assert SUMMARY["units_rezoning"] == int(RANK.units_rezoning.sum())
    assert math.isclose(SUMMARY["total_developable_ha"], RANK.dev_ha.sum(), abs_tol=0.01)


def test_blocked_sites_are_exactly_the_zero_storey_ones():
    blocked = set(SITES[SITES.height_storeys == 0].name)
    assert {b["name"] for b in SUMMARY["blocked_sites"]} == blocked
    assert SUMMARY["sites_blocked_by_zoning"] == len(blocked)


# ---------------------------------------------------------------- sensitivity
def test_sensitivity_intervals_bracket_the_base_rank():
    for f, lo, hi in [("sensitivity.csv", "rank_p05", "rank_p95"),
                      ("input_sensitivity.csv", "in_rank_p05", "in_rank_p95")]:
        d = pd.read_csv(ROOT / "outputs" / f)
        assert len(d) == N, f
        assert (d[lo] <= d[hi]).all(), f
        assert (d[lo] >= 1).all() and (d[hi] <= N).all(), f


def test_input_uncertainty_is_wider_than_weight_uncertainty():
    """The honest headline: what goes in matters more than how it is weighted."""
    w = pd.read_csv(ROOT / "outputs" / "sensitivity.csv")
    i = pd.read_csv(ROOT / "outputs" / "input_sensitivity.csv")
    assert (i.in_rank_p95 - i.in_rank_p05).mean() > (w.rank_p95 - w.rank_p05).mean()


# ---------------------------------------------------------------- built pages
def test_artifact_build_is_pure_ascii():
    """The Artifact build gets no charset meta, so any UTF-8 renders as mojibake."""
    p = ROOT / "docs" / "_atlas.artifact.html"
    if not p.exists():
        pytest.skip("artifact build not present; run build_atlas_payload.py")
    bad = [c for c in p.read_text(encoding="utf-8") if ord(c) > 127]
    assert not bad, f"{len(bad)} non-ASCII characters"


def test_standalone_build_has_a_viewport_meta():
    """Without it a phone lays the page out at 980px and zooms out."""
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html and "<!doctype html>" in html.lower()


def test_geojson_matches_the_rankings():
    gj = json.loads((ROOT / "outputs" / "candidate_sites.geojson").read_text())
    assert len(gj["features"]) == N
    keys = {frozenset(f["properties"]) for f in gj["features"]}
    assert len(keys) == 1, "features disagree on which properties they carry"
    for f in gj["features"]:
        assert not any(v is None for v in f["properties"].values())


def test_model_reproduces_the_committed_ranking():
    """Rebuilding from the source CSV must reproduce outputs/site_rankings.csv.

    Done in-process on a copy: a test must never rewrite the project's outputs,
    or a failure in one test silently corrupts the inputs of the next.
    """
    rebuilt, _, _ = M.build(SITES.copy())
    got = rebuilt.set_index("site_id")["rank_efficiency"]
    want = RANK.set_index("site_id")["rank"]
    assert got.loc[want.index].tolist() == want.tolist()


def test_build_is_deterministic():
    a = M.build(SITES.copy())[0]["rank_efficiency"].tolist()
    b = M.build(SITES.copy())[0]["rank_efficiency"].tolist()
    assert a == b


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
