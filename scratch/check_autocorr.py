import glob
import numpy as np
from PIL import Image

def spatial_autocorr(im):
    arr = np.array(im.convert("L"), dtype=np.float32)
    # correlation between pixel (i, j) and (i, j+1)
    diff = np.mean(np.abs(arr[:, :-1] - arr[:, 1:]))
    std = np.std(arr)
    return diff / (std + 1e-5)

for c in ["coal", "manganese", "iron_ore", "bauxite"]:
    f = glob.glob(f"data/test/{c}/*.*")[0]
    print(f"Real {c} roughness ratio: {spatial_autocorr(Image.open(f)):.3f}")

noise_im = Image.fromarray(np.clip(np.random.normal(128, 40, (224, 224, 3)), 0, 255).astype(np.uint8))
print(f"Noise roughness ratio: {spatial_autocorr(noise_im):.3f}")
