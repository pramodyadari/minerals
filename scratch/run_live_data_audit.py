"""
Master Live-Data Audit Script
Tests all four minerals (Coal, Manganese, Iron Ore, Bauxite) across:
1. Manuguru, Telangana (17.9820, 80.7450)
2. Balaghat, Madhya Pradesh (21.9048, 80.1849)
3. Additional relevant mineral provinces:
   - Jharia Coalfield, Jharkhand (23.7500, 86.4200) for Coal
   - Barbil / Keonjhar, Odisha (22.1200, 85.4000) for Manganese
   - Noamundi / Bailadila (22.1500, 85.5000) for Iron Ore
   - Panchpatmali Plateau, Odisha (18.8200, 83.0200) for Bauxite
"""

import sys
import os
import json
import math

sys.path.insert(0, os.path.abspath("."))

from backend.app.mineral_service import analyze_location_for_mineral

def point_in_polygon(lon: float, lat: float, poly_coords: list) -> bool:
    """Standard ray-casting algorithm to test if point is inside GeoFootprint polygon."""
    n = len(poly_coords)
    inside = False
    p1x, p1y = poly_coords[0][0], poly_coords[0][1]
    for i in range(n + 1):
        p2x, p2y = poly_coords[i % n][0], poly_coords[i % n][1]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lon <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

audit_targets = [
    # Manuguru, Telangana
    {"loc": "Manuguru, Telangana", "lat": 17.9820, "lon": 80.7450, "mineral": "Coal", "radius": 10.0},
    {"loc": "Manuguru, Telangana", "lat": 17.9820, "lon": 80.7450, "mineral": "Manganese", "radius": 10.0},
    {"loc": "Manuguru, Telangana", "lat": 17.9820, "lon": 80.7450, "mineral": "Iron Ore", "radius": 10.0},
    {"loc": "Manuguru, Telangana", "lat": 17.9820, "lon": 80.7450, "mineral": "Bauxite", "radius": 10.0},

    # Balaghat, Madhya Pradesh
    {"loc": "Balaghat, Madhya Pradesh", "lat": 21.9048, "lon": 80.1849, "mineral": "Manganese", "radius": 5.0},
    {"loc": "Balaghat, Madhya Pradesh", "lat": 21.9048, "lon": 80.1849, "mineral": "Coal", "radius": 10.0},
    {"loc": "Balaghat, Madhya Pradesh", "lat": 21.9048, "lon": 80.1849, "mineral": "Iron Ore", "radius": 10.0},
    {"loc": "Balaghat, Madhya Pradesh", "lat": 21.9048, "lon": 80.1849, "mineral": "Bauxite", "radius": 10.0},

    # Additional Provinces
    {"loc": "Jharia Coalfield, Jharkhand", "lat": 23.7500, "lon": 86.4200, "mineral": "Coal", "radius": 10.0},
    {"loc": "Barbil / Keonjhar, Odisha", "lat": 22.1200, "lon": 85.4000, "mineral": "Manganese", "radius": 10.0},
    {"loc": "Noamundi Iron Belt, Jharkhand", "lat": 22.1500, "lon": 85.5000, "mineral": "Iron Ore", "radius": 10.0},
    {"loc": "Panchpatmali Bauxite Plateau, Odisha", "lat": 18.8200, "lon": 83.0200, "mineral": "Bauxite", "radius": 10.0},
]

results = []

print("=" * 80)
print("EXECUTING LIVE-DATA AUDIT ACROSS ALL TEST TARGETS")
print("=" * 80)

for idx, t in enumerate(audit_targets, 1):
    print(f"\n--- [{idx}/{len(audit_targets)}] Target: {t['loc']} | Mineral: {t['mineral']} ---")
    res = analyze_location_for_mineral(
        location_name=t["loc"],
        lat=t["lat"],
        lon=t["lon"],
        mineral_name=t["mineral"],
        radius_km=t["radius"]
    )

    scenes = res.get("satellite_scenes", [])
    sat_status = res.get("satellite_imagery_availability")
    geo_status = res.get("geological_evidence_availability")
    model_cov = res.get("model_coverage")
    pred_avail = res.get("prediction_availability")
    pred = res.get("prediction")
    overall = res.get("overall_status")
    pixels_processed = res.get("raster_pixels_processed", False)

    first_scene = scenes[0] if scenes else None
    footprint_intersects = False
    if first_scene and first_scene.get("geofootprint"):
        gf = first_scene["geofootprint"]
        if gf.get("type") == "Polygon" and gf.get("coordinates"):
            footprint_intersects = point_in_polygon(t["lon"], t["lat"], gf["coordinates"][0])

    record = {
        "index": idx,
        "location": t["loc"],
        "coordinates": f"{t['lat']:.4f}°N, {t['lon']:.4f}°E",
        "radius_km": t["radius"],
        "mineral": t["mineral"],
        "overall_status": overall,
        "satellite_imagery_availability": sat_status,
        "geological_evidence_availability": geo_status,
        "model_coverage": model_cov,
        "prediction_availability": pred_avail,
        "prediction_score": pred["prospectivity_index"] if pred else None,
        "prediction_classification": pred["classification"] if pred else None,
        "raster_pixels_processed": pixels_processed,
        "raster_processing_status": res.get("raster_processing_status"),
        "satellite_scene_id": first_scene["scene_id"] if first_scene else None,
        "satellite_tile": first_scene["tile_id"] if first_scene else None,
        "satellite_acq_date": first_scene["acquisition_date"] if first_scene else None,
        "satellite_cloud_pct": first_scene["cloud_cover_pct"] if first_scene else None,
        "satellite_footprint_intersects": footprint_intersects,
        "catalogue_http_status": res.get("satellite_catalogue_http_status"),
        "catalogue_timestamp": res.get("satellite_catalogue_response_timestamp"),
        "documented_occurrences_count": len(res.get("documented_occurrences", [])),
        "nearest_occurrence": res.get("documented_occurrences", [])[0]["name"] if res.get("documented_occurrences") else None,
        "nearest_occurrence_distance_km": res.get("documented_occurrences", [])[0]["distance_km"] if res.get("documented_occurrences") else None,
        "nearest_occurrence_verification": res.get("documented_occurrences", [])[0].get("verification_status") if res.get("documented_occurrences") else None,
        "nearest_occurrence_source": res.get("documented_occurrences", [])[0].get("source_title") if res.get("documented_occurrences") else None,
        "geological_source_org": res.get("geological_source_attribution", {}).get("source"),
        "geological_pub_year": res.get("geological_source_attribution", {}).get("publication_year"),
        "geological_scale": res.get("geological_source_attribution", {}).get("map_scale")
    }
    results.append(record)

    print(f"Overall Status: {overall}")
    print(f"Coverage: Satellite={sat_status} | Geology={geo_status} | Model={model_cov} | Pred={pred_avail}")
    print(f"Prediction: {record['prediction_score']} (Pixels Processed: {pixels_processed})")
    if first_scene:
        print(f"Scene: {first_scene['scene_id']} (Tile: {first_scene['tile_id']}, Cloud: {first_scene['cloud_cover_pct']}%, Intersects: {footprint_intersects})")
    if record["nearest_occurrence"]:
        print(f"Nearest Deposit: {record['nearest_occurrence']} ({record['nearest_occurrence_distance_km']} km away) [Status: {record['nearest_occurrence_verification']}]")

with open("scratch/audit_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 80)
print(f"AUDIT COMPLETE — {len(results)} TARGET AUDIT RECORDS SAVED TO scratch/audit_results.json")
print("=" * 80)
