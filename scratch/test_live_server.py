import httpx

url = "http://127.0.0.1:8001/classify-image"

with httpx.Client() as client:
    # Test 1: Bauxite
    with open("data/test/bauxite/bauxite_test_000.jpg", "rb") as f:
        res_b = client.post(url, files={"file": ("bauxite.jpg", f, "image/jpeg")}).json()
    print("Live Bauxite:", res_b["status"], "Supported:", res_b["is_supported_mineral"], "Mineral:", res_b["predicted_mineral"], "Dist:", res_b["feature_distance"])

    # Test 2: Basalt
    with open("data/evaluation/ood/basalt/basalt_000.jpg", "rb") as f:
        res_ba = client.post(url, files={"file": ("basalt.jpg", f, "image/jpeg")}).json()
    print("Live Basalt:", res_ba["status"], "Supported:", res_ba["is_supported_mineral"], "Mineral:", res_ba["predicted_mineral"], "Dist:", res_ba["feature_distance"], "Closest:", res_ba["closest_candidate_mineral"])

    # Test 3: Sandstone
    with open("data/evaluation/ood/sandstone/sandstone_000.jpg", "rb") as f:
        res_sa = client.post(url, files={"file": ("sandstone.jpg", f, "image/jpeg")}).json()
    print("Live Sandstone:", res_sa["status"], "Supported:", res_sa["is_supported_mineral"], "Mineral:", res_sa["predicted_mineral"], "Dist:", res_sa["feature_distance"], "Closest:", res_sa["closest_candidate_mineral"])
