import glob, os, numpy as np
from PIL import Image

for f in glob.glob("data/test/manganese/*.*")[:3]:
    im = Image.open(f).convert("RGB")
    arr = np.array(im, dtype=np.float32)
    h, w, _ = arr.shape
    bh, bw = int(h * 0.1), int(w * 0.1)
    
    border_pixels = np.concatenate([
        arr[:bh, :].reshape(-1, 3),
        arr[-bh:, :].reshape(-1, 3),
        arr[:, :bw].reshape(-1, 3),
        arr[:, -bw:].reshape(-1, 3)
    ], axis=0)
    
    center_pixels = arr[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)].reshape(-1, 3)
    
    border_mean = border_pixels.mean(axis=0)
    center_mean = center_pixels.mean(axis=0)
    diff = np.linalg.norm(center_mean - border_mean)
    print(f"{os.path.basename(f)}: border_mean={border_mean}, center_mean={center_mean}, diff={diff:.2f}")

# Now check coal upload
f = "data/uploads/20261028_134742_70df91e2acfb_Bituminous_Coal.jpg"
im = Image.open(f).convert("RGB")
arr = np.array(im.resize((512, 384)), dtype=np.float32)
h, w, _ = arr.shape
bh, bw = int(h * 0.1), int(w * 0.1)
border_pixels = np.concatenate([
    arr[:bh, :].reshape(-1, 3),
    arr[-bh:, :].reshape(-1, 3),
    arr[:, :bw].reshape(-1, 3),
    arr[:, -bw:].reshape(-1, 3)
], axis=0)
center_pixels = arr[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)].reshape(-1, 3)
border_mean = border_pixels.mean(axis=0)
center_mean = center_pixels.mean(axis=0)
diff = np.linalg.norm(center_mean - border_mean)
print(f"Coal Upload: border_mean={border_mean}, center_mean={center_mean}, diff={diff:.2f}")

