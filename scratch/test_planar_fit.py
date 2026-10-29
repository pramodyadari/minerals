import numpy as np
from PIL import Image
from scipy import ndimage

# Test planar background fitting or large gaussian illumination estimation

# Let's recreate uneven lighting image
w, h = 600, 400
img_uneven = Image.new("RGB", (w, h), (240, 240, 240))
from PIL import ImageDraw
draw = ImageDraw.Draw(img_uneven)
for x in range(w):
    val = int(250 - (x / w) * 80)
    draw.line([(x, 0), (x, h)], fill=(val, val, val))
rock = np.random.normal(loc=50, scale=10, size=(180, 260, 3)).clip(10, 80).astype(np.uint8)
img_uneven.paste(Image.fromarray(rock), (170, 110))

arr = np.array(img_uneven, dtype=np.float32)
lum = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]

# Estimate background illumination using large median / percentile filter or large gaussian
# Border pixels are known to be background
bw = int(w * 0.08)
bh = int(h * 0.08)

# Sample perimeter
border_coords = []
border_vals = []
for y in range(h):
    for x in range(w):
        if y < bh or y >= h - bh or x < bw or x >= w - bw:
            border_coords.append([x, y, 1.0])
            border_vals.append(lum[y, x])

A = np.array(border_coords)
b = np.array(border_vals)
# Fit plane: lum = a*x + b*y + c
plane, res, _, _ = np.linalg.lstsq(A, b, rcond=None)
print("Fitted plane parameters (a, b, c):", plane)

# Compute plane across whole image
xx, yy = np.meshgrid(np.arange(w), np.arange(h))
fitted_bg = plane[0] * xx + plane[1] * yy + plane[2]
diff = fitted_bg - lum

# Residuals on border
border_res = np.abs(lum[A[:,1].astype(int), A[:,0].astype(int)] - fitted_bg[A[:,1].astype(int), A[:,0].astype(int)])
print("Border fit residual std:", border_res.std(), "max:", border_res.max())

# Detect rock where lum is significantly below fitted background
is_rock = diff > max(35.0, 3.5 * border_res.std())
labeled, num_features = ndimage.label(is_rock)
print("Num features detected with planar background correction:", num_features)
sizes = ndimage.sum(is_rock, labeled, range(1, num_features + 1))
max_idx = int(np.argmax(sizes))
target_mask = (labeled == (max_idx + 1)).astype(np.int32)
locs = ndimage.find_objects(target_mask)
print("Detected bounding box:", locs[0])
