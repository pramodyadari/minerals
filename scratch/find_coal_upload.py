from pathlib import Path
import sys
import hashlib
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
UPLOAD_DIR = ROOT / "data" / "uploads"

from backend.app.vision_service import classify_specimen_image

print(f"Project: {ROOT}")
print(f"Upload directory: {UPLOAD_DIR}")

if not UPLOAD_DIR.exists():
    print("ERROR: Upload directory does not exist.")
    raise SystemExit(1)

uploads = sorted(
    [p for p in UPLOAD_DIR.iterdir() if p.is_file()],
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

print(f"\nTotal uploads found: {len(uploads)}")
matches = 0
errors = 0

for path in uploads:
    try:
        data = path.read_bytes()
        result = classify_specimen_image(data)

        probabilities = result.get("class_probabilities_pct") or {}
        bauxite_score = probabilities.get("Bauxite", 0)
        distance = result.get("feature_distance")
        candidate = result.get("closest_candidate")
        status = result.get("identification_status")

        print(f"\nFile: {path.name}")
        print(f"  SHA-256: {hashlib.sha256(data).hexdigest()}")
        print(f"  Probabilities: {probabilities}")
        print(f"  Closest candidate: {candidate}")
        print(f"  Feature distance: {distance}")
        print(f"  Identification status: {status}")

        if (
            (distance is not None and abs(float(distance) - 11.81) < 0.5)
            or abs(float(bauxite_score or 0) - 99.52) < 1.0
            or ("coal" in path.name.lower()
                and distance is not None
                and float(distance) > 5.0)
        ):
            matches += 1
            print("  *** POTENTIAL MATCH — inspect this result ***")

    except Exception as exc:
        errors += 1
        print(f"\nERROR processing {path.name}: {exc}")
        traceback.print_exc()

print(f"\nPotential matches: {matches}")
print(f"Processing errors: {errors}")
