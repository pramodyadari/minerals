import urllib.request
import json

def test_live_smoke():
    base_url = "http://127.0.0.1:8000"
    
    # 1. Test multi-mineral analysis endpoint with custom 3 minerals: Coal, Manganese, Iron Ore at 10 km
    payload = {
        "location_name": "Balaghat Survey Center",
        "latitude": 21.9455,
        "longitude": 80.4295,
        "radius_km": 10.0,
        "minerals": ["Coal", "Manganese", "Iron Ore"]
    }
    req = urllib.request.Request(
        f"{base_url}/analyze/multi",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    print("Testing /analyze/multi with custom minerals ['Coal', 'Manganese', 'Iron Ore'] at 10 km...")
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode())
        print(f"Status: {resp.status}, overall_status: {res.get('overall_status')}")
        print(f"Requested minerals: {res.get('requested_minerals')}")
        for min_name, m_data in res.get("minerals", {}).items():
            ev = m_data.get("evaluation_summary", {})
            print(f"  [{min_name}] Prospectivity Score: {ev.get('prospectivity_score')} (Status: {ev.get('prospectivity_status')}), "
                  f"Evidence Index: {ev.get('evidence_index')}, Quality: {ev.get('evidence_quality')}")

    # 2. Compare Balaghat Manganese across 1, 5, 10, and 25 km
    print("\nComparing Balaghat (21.9455, 80.4295) Manganese across 1, 5, 10, 25 km:")
    for r in [1.0, 5.0, 10.0, 25.0]:
        single_payload = {
            "location_name": "Balaghat",
            "latitude": 21.9455,
            "longitude": 80.4295,
            "mineral": "Manganese",
            "radius_km": r
        }
        s_req = urllib.request.Request(
            f"{base_url}/analyze",
            data=json.dumps(single_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(s_req, timeout=30) as s_resp:
            s_res = json.loads(s_resp.read().decode())
            ev = s_res.get("evaluation_summary", {})
            occs = s_res.get("documented_occurrences", [])
            occs_inside = [o for o in occs if o.get("is_inside_radius")]
            print(f"  Radius {r:4.1f} km -> Area: {s_res.get('area_sq_km')} sq km, "
                  f"AI Prospectivity: {ev.get('prospectivity_score')} ({ev.get('prospectivity_status')}), "
                  f"Evidence Index: {ev.get('evidence_index')}, "
                  f"Occurrences in radius: {len(occs_inside)} (Total nearby: {len(occs)})")

if __name__ == "__main__":
    test_live_smoke()
