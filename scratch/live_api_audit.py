"""
Comprehensive Live API Verification & Scientific Scoring Audit Script
Tests radii: 1, 5, 10, 25, 50 km for both /analyze-all and /analyze.
Target Coordinates: Balaghat Manganese Corridor (21.9048 N, 80.1849 E)
Second Target: Noamundi Iron Ore (22.1500 N, 85.5000 E)
"""

import urllib.request
import json
import math
import time

BASE_URL = "http://127.0.0.1:8000"
RADII = [1.0, 5.0, 10.0, 25.0, 50.0]

def query_api(endpoint, payload):
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        elapsed = time.time() - t0
        status_code = resp.getcode()
        body = json.loads(resp.read().decode("utf-8"))
        return status_code, elapsed, body

def run_audit():
    print("=" * 80)
    print("LIVE API AND UI VERIFICATION ACROSS RADII (1, 5, 10, 25, 50 km)")
    print("=" * 80)

    # 1. Multi-mineral endpoint (/analyze-all) for Balaghat
    balaghat_results = []
    lat = 21.9048
    lon = 80.1849
    loc_name = "Balaghat Mining Belt, Madhya Pradesh, India"

    print("\n--- Testing Balaghat Corridor (Manganese primary, All 4 Minerals) ---")
    for r in RADII:
        payload = {
            "location_name": loc_name,
            "latitude": lat,
            "longitude": lon,
            "radius_km": r
        }
        status_code, elapsed, data = query_api("/analyze-all", payload)
        
        calc_area = round(math.pi * (r ** 2), 2)
        reported_area = data.get("survey_area_sq_km")
        cache_hit = data.get("cache_hit", False)
        cache_key = data.get("cache_key")
        
        minerals = data.get("minerals", {})
        mn = minerals.get("Manganese", {})
        fe = minerals.get("Iron Ore", {})
        coal = minerals.get("Coal", {})
        baux = minerals.get("Bauxite", {})
        
        mn_eval = mn.get("evaluation_summary", {})
        fe_eval = fe.get("evaluation_summary", {})
        coal_eval = coal.get("evaluation_summary", {})
        baux_eval = baux.get("evaluation_summary", {})
        
        grid_3d = mn.get("prospectivity_grid", {})
        raster_cov = mn.get("raster_pixel_coverage", {})
        terrain = mn.get("terrain_evidence", {})
        
        entry = {
            "radius_km": r,
            "calculated_area_sq_km": calc_area,
            "reported_area_sq_km": reported_area,
            "http_status": status_code,
            "elapsed_seconds": round(elapsed, 3),
            "cache_hit": cache_hit,
            "cache_key": cache_key,
            "manganese": {
                "prospectivity_score": mn_eval.get("prospectivity_score"),
                "prospectivity_status": mn_eval.get("prospectivity_status"),
                "prediction_type": mn.get("prediction", {}).get("prediction_type"),
                "evidence_favorability_index": mn_eval.get("evidence_index"),
                "evidence_formula": mn_eval.get("evidence_formula"),
                "evidence_quality": mn_eval.get("evidence_quality"),
                "occurrences_in_radius": mn.get("occurrences_in_radius", mn.get("geological_evidence", {}).get("occurrences_in_radius_count")),
                "occurrences_total": mn.get("geological_evidence", {}).get("occurrences_total", len(mn.get("documented_occurrences", []))),
                "nearest_occurrence_km": mn.get("nearest_occurrence_km"),
                "raster_pixels_total": raster_cov.get("total_pixels_in_radius"),
                "raster_pixels_valid": raster_cov.get("valid_pixels"),
                "raster_resolution_m": raster_cov.get("pixel_resolution_m"),
                "terrain_status": terrain.get("status"),
                "terrain_elev_mean_m": terrain.get("elev_mean_m"),
                "terrain_relief_window_m": terrain.get("relief_window_m"),
                "3d_grid_status": grid_3d.get("status"),
                "3d_grid_radius_km": grid_3d.get("radius_km"),
                "3d_grid_resolution_m": grid_3d.get("resolution_m"),
                "3d_grid_rows": grid_3d.get("rows"),
                "3d_grid_cols": grid_3d.get("cols")
            },
            "safeguards_check": {
                "iron_ore_score": fe_eval.get("prospectivity_score"),
                "iron_ore_status": fe_eval.get("prospectivity_status"),
                "iron_ore_evidence_index": fe_eval.get("evidence_index"),
                "iron_ore_occurrences_in_radius": fe.get("occurrences_in_radius", 0),
                "coal_score": coal_eval.get("prospectivity_score"),
                "coal_status": coal_eval.get("prospectivity_status"),
                "coal_evidence_index": coal_eval.get("evidence_index"),
                "coal_occurrences_in_radius": coal.get("occurrences_in_radius", 0),
                "bauxite_score": baux_eval.get("prospectivity_score"),
                "bauxite_status": baux_eval.get("prospectivity_status"),
                "bauxite_evidence_index": baux_eval.get("evidence_index"),
                "bauxite_occurrences_in_radius": baux.get("occurrences_in_radius", 0)
            }
        }
        balaghat_results.append(entry)
        
        print(f"\n[Radius {r} km | Area: {calc_area} km²]")
        print(f"  HTTP: {status_code} ({elapsed:.2f}s) | Cache Hit: {cache_hit} | Key: {cache_key}")
        print(f"  Manganese AI Score (Point): {entry['manganese']['prospectivity_score']} ({entry['manganese']['prospectivity_status']})")
        print(f"  Manganese Evidence Index (Regional): {entry['manganese']['evidence_favorability_index']}")
        print(f"  Occurrences inside circle: Mn={entry['manganese']['occurrences_in_radius']}, Fe={entry['safeguards_check']['iron_ore_occurrences_in_radius']}, Coal={entry['safeguards_check']['coal_occurrences_in_radius']}, Bauxite={entry['safeguards_check']['bauxite_occurrences_in_radius']}")
        print(f"  Raster Pixels: {entry['manganese']['raster_pixels_valid']} / {entry['manganese']['raster_pixels_total']}")
        print(f"  3D Grid: status={entry['manganese']['3d_grid_status']}, radius={entry['manganese']['3d_grid_radius_km']} km, size={entry['manganese']['3d_grid_rows']}x{entry['manganese']['3d_grid_cols']}")
        print(f"  Safeguards: Fe ML={entry['safeguards_check']['iron_ore_score']}, Coal ML={entry['safeguards_check']['coal_score']}, Bauxite ML={entry['safeguards_check']['bauxite_score']}")

    # Second target: Noamundi (Iron Ore focal area with Copernicus DEM rasters on disk)
    print("\n--- Testing Noamundi Region (Iron Ore focal, DEM raster available on disk) ---")
    noamundi_results = []
    n_lat = 22.1500
    n_lon = 85.5000
    n_loc = "Noamundi Iron Ore Mine, Jharkhand"
    for r in RADII:
        payload = {
            "location_name": n_loc,
            "latitude": n_lat,
            "longitude": n_lon,
            "radius_km": r
        }
        status_code, elapsed, data = query_api("/analyze-all", payload)
        fe = data.get("minerals", {}).get("Iron Ore", {})
        mn = data.get("minerals", {}).get("Manganese", {})
        fe_eval = fe.get("evaluation_summary", {})
        terrain = fe.get("terrain_evidence", {})
        
        n_entry = {
            "radius_km": r,
            "area_sq_km": round(math.pi * (r ** 2), 2),
            "fe_prospectivity_score": fe_eval.get("prospectivity_score"),
            "fe_prospectivity_status": fe_eval.get("prospectivity_status"),
            "fe_evidence_index": fe_eval.get("evidence_index"),
            "fe_occurrences_in_radius": fe.get("occurrences_in_radius", 0),
            "mn_prospectivity_score": mn.get("evaluation_summary", {}).get("prospectivity_score"),
            "mn_prospectivity_status": mn.get("evaluation_summary", {}).get("prospectivity_status"),
            "terrain_relief_window_m": terrain.get("relief_window_m"),
            "terrain_elev_mean_m": terrain.get("elev_mean_m"),
            "terrain_status": terrain.get("status")
        }
        noamundi_results.append(n_entry)
        print(f"\n[Noamundi Radius {r} km]")
        print(f"  Iron Ore ML Score: {n_entry['fe_prospectivity_score']} ({n_entry['fe_prospectivity_status']})")
        print(f"  Iron Ore Evidence Index: {n_entry['fe_evidence_index']}")
        print(f"  Iron Ore Occurrences in radius: {n_entry['fe_occurrences_in_radius']}")
        print(f"  DEM Terrain: relief={n_entry['terrain_relief_window_m']} m, mean={n_entry['terrain_elev_mean_m']} m, status={n_entry['terrain_status']}")
        print(f"  Manganese ML Score at Noamundi (Outside T44QMK Footprint): {n_entry['mn_prospectivity_score']} ({n_entry['mn_prospectivity_status']})")

    out_data = {
        "balaghat_audit": balaghat_results,
        "noamundi_audit": noamundi_results
    }
    with open("scratch/live_verification_audit_full.json", "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)
    print("\nSuccessfully saved full live audit report to scratch/live_verification_audit_full.json")

if __name__ == "__main__":
    run_audit()
