import httpx

with httpx.Client() as client:
    res = client.get("http://127.0.0.1:8001/minerals").json()
    print("Minerals count:", res["total_classes"])

    res_zones = client.get("http://127.0.0.1:8001/candidate-zones").json()
    print("Candidate zones count:", len(res_zones))

    # Test analyze for Balaghat
    res_ana = client.post(
        "http://127.0.0.1:8001/analyze",
        json={"latitude": 21.8, "longitude": 80.2, "radius_km": 5.0, "mineral": "Manganese"}
    ).json()
    print("Analyze status:", res_ana.get("status"), "Prospectivity level:", res_ana.get("prospectivity_level"))
