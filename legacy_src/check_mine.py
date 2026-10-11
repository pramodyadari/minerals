import os
import rasterio

# Resolve robust paths relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIF_PATH = os.path.join(BASE_DIR, "outputs", "manganese_prospectivity.tif")
NPY_PATH = os.path.join(BASE_DIR, "data", "processed", "prospectivity_map.npy")

# Known Ghondi mine pixel
row = 3655
col = 2056

if os.path.exists(TIF_PATH):
    with rasterio.open(TIF_PATH) as src:
        val = src.read(1, window=((row, row + 1), (col, col + 1)))
        value = float(val[0, 0])
elif os.path.exists(NPY_PATH):
    prospectivity = np.load(NPY_PATH)
    value = float(prospectivity[row, col])
else:
    raise FileNotFoundError(f"Neither {TIF_PATH} nor {NPY_PATH} found.")

print("Known mine pixel:")
print("Row:", row)
print("Column:", col)
print("Prospectivity:", value)

if value >= 0.7:
    print("Result: HIGH prospectivity")
elif value >= 0.4:
    print("Result: MEDIUM prospectivity")
else:
    print("Result: LOW prospectivity")