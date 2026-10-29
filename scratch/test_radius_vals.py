import sys, os
sys.path.insert(0, os.path.abspath("."))
os.environ["MOCK_CDSE_DISCOVERY"] = "1"

from backend.app.mineral_service import analyze_location_for_mineral
lat, lon = 21.9455, 80.4295
for r in [1.0, 5.0, 10.0, 25.0]:
    res = analyze_location_for_mineral('Balaghat', lat, lon, 'Manganese', r)
    es = res['evaluation_summary']
    occs_inside = [o for o in res['documented_occurrences'] if o.get('is_inside_radius')]
    print(f"Radius {r:4.1f} km: ML Prospectivity={es['prospectivity_score']}, Evidence Index={es['evidence_index']}, Occs inside radius={len(occs_inside)}, Total nearby occs={len(res['documented_occurrences'])}")
