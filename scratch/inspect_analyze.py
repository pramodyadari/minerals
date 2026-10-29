import httpx

with httpx.Client(timeout=30.0) as client:
    res = client.post(
        "http://127.0.0.1:8001/analyze",
        json={"latitude": 21.8, "longitude": 80.2, "radius_km": 5.0, "mineral": "Manganese", "location_name": "Balaghat Mine"}
    )
    data = res.json()
    print("All keys returned by /analyze:", list(data.keys()))
    for k in ["prospectivity", "prospectivity_index", "confidence", "geological_analysis", "terrain_analysis", "evidence"]:
        if k in data:
            print(f"  {k}: {data[k]}")
