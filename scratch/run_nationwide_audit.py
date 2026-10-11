"""
Nationwide Mineral Prospectivity Audit Script
Executes full pipeline across 12 diverse locations across India and territorial boundary edges.
"""

import os
import sys
import json
import time

project_root = r"c:\Users\yadar\Downloads\ai_mineral_explo"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.mineral_service import analyze_location_for_mineral

TEST_TARGETS = [
    {
        "id": "target_1_manuguru_coal",
        "name": "Manuguru, Telangana",
        "lat": 17.9820,
        "lon": 80.7450,
        "mineral": "Coal",
        "radius_km": 5.0,
        "region_type": "Known Mining Basin (Godavari Graben)"
    },
    {
        "id": "target_2_balaghat_manganese",
        "name": "Balaghat, Madhya Pradesh",
        "lat": 21.9048,
        "lon": 80.1849,
        "mineral": "Manganese",
        "radius_km": 5.0,
        "region_type": "Validated AI Model Domain (Tile T44QMK Sausar Belt)"
    },
    {
        "id": "target_3_noamundi_iron",
        "name": "Noamundi, Jharkhand",
        "lat": 22.1500,
        "lon": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 5.0,
        "region_type": "Known Major Mining Province (Singhbhum-North Odisha BIF)"
    },
    {
        "id": "target_4_panchpatmali_bauxite",
        "name": "Panchpatmali Plateau, Odisha",
        "lat": 18.8200,
        "lon": 83.0200,
        "mineral": "Bauxite",
        "radius_km": 5.0,
        "region_type": "World-Class Blanket Deposit (East Coast Khondalite Plateau)"
    },
    {
        "id": "target_5_jharia_coal",
        "name": "Jharia Coalfield, Jharkhand",
        "lat": 23.7500,
        "lon": 86.4200,
        "mineral": "Coal",
        "radius_km": 5.0,
        "region_type": "Known Major Coking Coal Basin (Damodar Valley)"
    },
    {
        "id": "target_6_barbil_manganese",
        "name": "Barbil / Keonjhar, Odisha",
        "lat": 22.1200,
        "lon": 85.4000,
        "mineral": "Manganese",
        "radius_km": 5.0,
        "region_type": "Known Manganese Corridor (Bonai-Keonjhar Belt)"
    },
    {
        "id": "target_7_bailadila_iron",
        "name": "Bailadila Ridge, Chhattisgarh",
        "lat": 18.7300,
        "lon": 81.2400,
        "mineral": "Iron Ore",
        "radius_km": 5.0,
        "region_type": "High-Grade Ridge Deposit (Bastar Craton)"
    },
    {
        "id": "target_8_amarkantak_bauxite",
        "name": "Amarkantak Plateau, Madhya Pradesh",
        "lat": 22.6800,
        "lon": 81.7600,
        "mineral": "Bauxite",
        "radius_km": 5.0,
        "region_type": "Deccan Basalt Residual Plateau (Central India)"
    },
    {
        "id": "target_9_jaipur_coal_greenfield",
        "name": "Jaipur, Rajasthan",
        "lat": 26.9124,
        "lon": 75.7873,
        "mineral": "Coal",
        "radius_km": 10.0,
        "region_type": "Greenfield / Non-Mining (Aravalli Orogenic Belt)"
    },
    {
        "id": "target_10_varanasi_iron_greenfield",
        "name": "Varanasi, Uttar Pradesh",
        "lat": 25.3176,
        "lon": 82.9739,
        "mineral": "Iron Ore",
        "radius_km": 10.0,
        "region_type": "Greenfield / Non-Mining (Indo-Gangetic Foreland Basin)"
    },
    {
        "id": "target_11_bengaluru_bauxite_greenfield",
        "name": "Bengaluru, Karnataka",
        "lat": 12.9716,
        "lon": 77.5946,
        "mineral": "Bauxite",
        "radius_km": 10.0,
        "region_type": "Greenfield / Non-Mining (Peninsular Gneissic Basement)"
    },
    {
        "id": "target_12_colombo_outside_india",
        "name": "Colombo, Sri Lanka",
        "lat": 6.9271,
        "lon": 79.8612,
        "mineral": "Manganese",
        "radius_km": 5.0,
        "region_type": "Outside Sovereign Indian Boundary Check"
    }
]

audit_results = []
print(f"Starting Nationwide Audit across {len(TEST_TARGETS)} target locations...\n")

for i, t in enumerate(TEST_TARGETS, 1):
    print(f"[{i}/{len(TEST_TARGETS)}] Auditing {t['name']} for {t['mineral']} ({t['lat']}°N, {t['lon']}°E)...")
    start_t = time.time()
    try:
        res = analyze_location_for_mineral(
            location_name=t["name"],
            lat=t["lat"],
            lon=t["lon"],
            mineral_name=t["mineral"],
            radius_km=t["radius_km"]
        )
        elapsed = round(time.time() - start_t, 2)
        
        # Extract critical audit fields
        scenes = res.get("satellite_scenes", [])
        primary_scene = scenes[0] if scenes else None
        
        audit_entry = {
            "target_num": i,
            "target_id": t["id"],
            "location_name": t["name"],
            "region_type": t["region_type"],
            "coordinates": f"{t['lat']}°N, {t['lon']}°E",
            "mineral": t["mineral"],
            "radius_km": t["radius_km"],
            "elapsed_sec": elapsed,
            "status": res.get("status"),
            "overall_status": res.get("overall_status"),
            "is_within_india": res.get("is_within_india", True),
            "satellite_imagery_availability": res.get("satellite_imagery_availability"),
            "catalogue_discovery": primary_scene.get("catalogue_discovery") if primary_scene else ("DISCOVERED_LIVE_CDSE" if scenes else "NOT_FOUND"),
            "primary_satellite_scene": primary_scene.get("scene_id") if primary_scene else None,
            "acquisition_date": primary_scene.get("acquisition_date") if primary_scene else None,
            "tile_id": primary_scene.get("tile_id") if primary_scene else None,
            "cloud_cover_pct": primary_scene.get("cloud_cover_pct") if primary_scene else None,
            "data_access_status": primary_scene.get("data_access_status") if primary_scene else "NOT_ACCESSED",
            "pixel_processing_status": primary_scene.get("pixel_processing_status") if primary_scene else "SKIPPED",
            "raster_pixels_processed": res.get("raster_pixels_processed", False),
            "geological_evidence_availability": res.get("geological_evidence_availability"),
            "geological_province": res.get("geological_province", {}).get("name") if res.get("geological_province") else None,
            "regional_terrane": res.get("regional_terrane", {}).get("name") if res.get("regional_terrane") else None,
            "documented_occurrences_count": len(res.get("documented_occurrences", [])),
            "nearest_occurrence": res.get("documented_occurrences", [{}])[0].get("name") if res.get("documented_occurrences") else None,
            "nearest_occurrence_km": res.get("nearest_occurrence_km"),
            "model_coverage": res.get("model_coverage"),
            "prediction_availability": res.get("prediction_availability"),
            "prediction_score_pct": res.get("prediction", {}).get("prospectivity_index") if res.get("prediction") else None,
            "confidence_score": res.get("confidence_score"),
            "reason_for_withheld_prediction": res.get("message") if not res.get("prediction") else None,
            "absence_of_mine_records_assessment": res.get("absence_of_mine_records_assessment")
        }
        audit_results.append(audit_entry)
        print(f"  -> Done in {elapsed}s | Status: {audit_entry['status']} | Model Cov: {audit_entry['model_coverage']} | Score: {audit_entry['prediction_score_pct']}")
    except Exception as e:
        print(f"  -> ERROR: {e}")
        audit_results.append({
            "target_num": i,
            "target_id": t["id"],
            "location_name": t["name"],
            "error": str(e)
        })

out_json = os.path.join(project_root, "scratch", "nationwide_audit_results.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(audit_results, f, indent=2)

print(f"\nAudit completed. Results saved to {out_json}")
