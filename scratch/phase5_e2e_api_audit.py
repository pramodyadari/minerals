import os
import sys
import json
from fastapi.testclient import TestClient

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
sys.path.insert(0, os.path.join(BASE_DIR, "backend", "app"))

from main import app

client = TestClient(app)

audit_results = {
    "timestamp": "2026-10-29T22:02:00Z",
    "tests_run": [],
    "summary": {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
}

def record_test(name, passed, details=None):
    audit_results["tests_run"].append({
        "test_name": name,
        "passed": passed,
        "details": details or {}
    })
    if passed:
        audit_results["summary"]["passed"] += 1
    else:
        audit_results["summary"]["failed"] += 1
        audit_results["summary"]["errors"].append(name)
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")

# 1. Health Checks
r = client.get("/health")
record_test("GET /health", r.status_code == 200 and r.json().get("status") in ["healthy", "ok"], r.json())

r = client.get("/api/health")
record_test("GET /api/health", r.status_code == 200 and r.json().get("status") in ["healthy", "ok"], r.json())

# 2. Minerals list
r = client.get("/minerals")
record_test("GET /minerals", r.status_code == 200 and len(r.json().get("minerals", [])) == 4, {"count": len(r.json().get("minerals", []))})

# 3. Model Registry & Checkpoint Verification
r = client.get("/api/models/registry")
reg_data = r.json()
record_test("GET /api/models/registry", r.status_code == 200 and "registered_models" in reg_data, {
    "registered_models_count": len(reg_data.get("registered_models", []))
})

# 4. Outside India Territory
r = client.post("/analyze", json={
    "location_name": "London UK",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "mineral": "Manganese",
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
record_test("POST /analyze Outside India Territory", r.status_code == 200 and res.get("status") == "OUTSIDE_INDIA_TERRITORY" and res.get("confidence_score") is None, {
    "status": res.get("status"),
    "confidence_score": res.get("confidence_score")
})

# 5. Manganese Inside Training Footprint (Balaghat)
r = client.post("/analyze", json={
    "location_name": "Balaghat",
    "latitude": 21.8000,
    "longitude": 80.1800,
    "mineral": "Manganese",
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
pred = res.get("prediction")
record_test("POST /analyze Manganese Inside Footprint (Relative Score)", r.status_code == 200 and res.get("model_coverage") == "VALIDATED_ACTIVE" and pred is not None and "prospectivity_index" in pred and res.get("confidence_score") is None, {
    "coverage": res.get("model_coverage"),
    "prospectivity_index": pred.get("prospectivity_index") if pred else None,
    "calibrated_confidence_withheld": res.get("confidence_score") is None
})

# 6. Manganese Outside Training Footprint (Bangalore)
r = client.post("/analyze", json={
    "location_name": "Bangalore",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "mineral": "Manganese",
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
record_test("POST /analyze Manganese Outside Footprint", r.status_code == 200 and res.get("model_coverage") == "OUTSIDE_TRAINING_FOOTPRINT" and res.get("prediction") is None, {
    "coverage": res.get("model_coverage"),
    "overall_status": res.get("overall_status")
})

# 7. Coal Analysis in Jharia (Underground seam disclaimer check)
r = client.post("/analyze", json={
    "location_name": "Jharia",
    "latitude": 23.7400,
    "longitude": 86.4100,
    "mineral": "Coal",
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
disc = res.get("limitations_and_warnings", [])
has_coal_warning = any("underground coal seams" in w.lower() for w in disc)
record_test("POST /analyze Coal Geological Disclaimers", r.status_code == 200 and has_coal_warning, {
    "overall_status": res.get("overall_status"),
    "disclaimers_count": len(disc)
})

# 8. Iron Ore Analysis in Noamundi (Surface staining disclaimer check)
r = client.post("/analyze", json={
    "location_name": "Noamundi",
    "latitude": 22.1500,
    "longitude": 85.5000,
    "mineral": "Iron Ore",
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
disc = res.get("limitations_and_warnings", [])
has_iron_warning = any("ferric" in w.lower() or "staining" in w.lower() for w in disc)
record_test("POST /analyze Iron Ore Staining Disclaimers", r.status_code == 200 and has_iron_warning, {
    "overall_status": res.get("overall_status"),
    "disclaimers_count": len(disc)
})

# 9. Bauxite Analysis in Panchpatmali (Laterite disclaimer check)
r = client.post("/analyze", json={
    "location_name": "Panchpatmali",
    "latitude": 18.8500,
    "longitude": 83.0000,
    "mineral": "Bauxite",
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
disc = res.get("limitations_and_warnings", [])
has_bauxite_warning = any("laterite" in w.lower() or "duricrust" in w.lower() for w in disc)
record_test("POST /analyze Bauxite Laterite Disclaimers", r.status_code == 200 and has_bauxite_warning, {
    "overall_status": res.get("overall_status"),
    "disclaimers_count": len(disc)
})

# 10. Multi-Mineral All Four Run
r = client.post("/analyze-all", json={
    "location_name": "Noamundi",
    "latitude": 22.1500,
    "longitude": 85.5000,
    "radius_km": 10.0,
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
has_all_four = set(res.get("minerals", {}).keys()) == {"Coal", "Manganese", "Iron Ore", "Bauxite"}
record_test("POST /analyze-all Four Minerals", r.status_code == 200 and has_all_four, {
    "commodities": list(res.get("minerals", {}).keys())
})

# 11. Custom 2 Minerals Selection
r = client.post("/analyze-all", json={
    "location_name": "Noamundi",
    "latitude": 22.1500,
    "longitude": 85.5000,
    "radius_km": 10.0,
    "minerals": ["Coal", "Manganese"],
    "mock_satellite_error": "MOCK_MODE"
})
res = r.json()
record_test("POST /analyze-all Custom 2 Minerals", r.status_code == 200 and len(res.get("minerals", {})) == 2, {
    "commodities": list(res.get("minerals", {}).keys())
})

# 12. Invalid Custom 1 Mineral (Validation Error)
r = client.post("/analyze-all", json={
    "location_name": "Noamundi",
    "latitude": 22.1500,
    "longitude": 85.5000,
    "radius_km": 10.0,
    "minerals": ["Coal"]
})
record_test("POST /analyze-all Custom 1 Mineral Rejection (422)", r.status_code == 422, r.json())

# 13. Specimen Classification - Known Synthetic Coal
known_coal_path = os.path.join(BASE_DIR, "data", "test", "coal", "coal_test_000.jpg")
with open(known_coal_path, "rb") as fp:
    r = client.post("/classify-image", files={"file": ("coal.jpg", fp, "image/jpeg")})
res = r.json()
record_test("POST /classify-image Known Synthetic Coal Acceptance", r.status_code == 200 and res.get("identification_status") == "ACCEPTED" and res.get("identified_mineral") == "Coal", {
    "identified_mineral": res.get("identified_mineral"),
    "display_label": res.get("display_label"),
    "status": res.get("identification_status"),
    "accepted_confidence": res.get("accepted_confidence")
})

# 14. Specimen Classification - OOD Quartz Rejection
ood_quartz_path = os.path.join(BASE_DIR, "data", "evaluation", "ood", "quartz", "quartz_000.jpg")
with open(ood_quartz_path, "rb") as fp:
    r = client.post("/classify-image", files={"file": ("quartz.jpg", fp, "image/jpeg")})
res = r.json()
record_test("POST /classify-image OOD Quartz Rejection", r.status_code == 200 and res.get("identification_status") == "OUT_OF_DISTRIBUTION" and res.get("accepted_confidence") is None, {
    "display_label": res.get("display_label"),
    "status": res.get("identification_status"),
    "distance": res.get("feature_distance"),
    "nearest_candidate": res.get("nearest_candidate", {}).get("mineral")
})

# 15. Specimen Classification - Disputed Coal Field Upload Rejection
coal_upload_path = os.path.join(BASE_DIR, "data", "uploads", "20261028_134742_70df91e2acfb_Bituminous_Coal.jpg")
with open(coal_upload_path, "rb") as fp:
    r = client.post("/classify-image", files={"file": ("Bituminous_Coal.jpg", fp, "image/jpeg")})
res = r.json()
record_test("POST /classify-image Disputed Coal Upload Rejection", r.status_code == 200 and res.get("identification_status") == "OUT_OF_DISTRIBUTION" and res.get("feature_distance", 0) > 5.0, {
    "display_label": res.get("display_label"),
    "status": res.get("identification_status"),
    "distance": res.get("feature_distance"),
    "raw_favored": res.get("rejection_explanation", {}).get("cnn_favored_mineral")
})

# 16. Specimen Classification - Corrupt File Handling
corrupt_path = os.path.join(BASE_DIR, "data", "uploads", "20261026_161014_625fe0608633_corrupt.jpg")
with open(corrupt_path, "rb") as fp:
    r = client.post("/classify-image", files={"file": ("corrupt.jpg", fp, "image/jpeg")})
record_test("POST /classify-image Corrupt File Rejection", r.status_code in [400, 422], {"status_code": r.status_code, "detail": r.json() if r.headers.get("content-type") == "application/json" else r.text})

# 17. Copernicus Missing Credentials State
r = client.get("/cdse-auth-status")
auth_status = r.json()
record_test("GET /cdse-auth-status Truthful Credentials Report", r.status_code == 200 and "authenticated" in auth_status, auth_status)

# 18. Evidence Reliability Endpoint
r = client.get("/api/evidence/reliability?latitude=21.8000&longitude=80.1800&mineral=Manganese")
ev_data = r.json()
record_test("GET /api/evidence/reliability", r.status_code == 200 and "model_reliability" in ev_data and "evidence_inventory" in ev_data, {
    "engine_version": ev_data.get("engine_version"),
    "eligibility_status": ev_data.get("model_reliability", {}).get("eligibility_status"),
    "layers_audited": ev_data.get("total_layers_audited")
})

with open("scratch/live_api_audit_phase5.json", "w") as fp:
    json.dump(audit_results, fp, indent=2)

print(f"\nPhase 5 API Audit: {audit_results['summary']['passed']} passed, {audit_results['summary']['failed']} failed.")
