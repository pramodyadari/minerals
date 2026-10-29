import sys, os
sys.path.insert(0, os.path.abspath("."))
os.environ["MOCK_CDSE_DISCOVERY"] = "1"

from backend.app.mineral_service import analyze_location_for_mineral
lat, lon = 21.9455, 80.4295
for r in [1.0, 5.0, 10.0, 25.0]:
    res = analyze_location_for_mineral('Balaghat', lat, lon, 'Manganese', r)
    es = res['evaluation_summary']
    print(f"Radius {r} km: evidence_index={es['evidence_index']}, subscores={es.get('subscores')}")
    print(f"  supporting: {es.get('main_supporting_evidence')}")
