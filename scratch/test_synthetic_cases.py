import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

def create_synthetic_test_case(case_type="white_card_dark_specimen"):
    """
    Creates synthetic test images with known ground truth bounding boxes.
    """
    w, h = 600, 400
    if case_type == "white_card_dark_specimen":
        # White card with slight gradient/shadow
        img = Image.new("RGB", (w, h), (230, 228, 226))
        draw = ImageDraw.Draw(img)
        # Add smooth shadow gradient on bottom
        for y in range(300, 400):
            val = int(226 - (y - 300) * 0.3)
            draw.line([(0, y), (w, y)], fill=(val, val, val))
        # Dark rock specimen in center: x in [150, 450], y in [100, 300]
        # Add rock texture
        rock = np.random.normal(loc=45, scale=8, size=(200, 300, 3)).clip(10, 80).astype(np.uint8)
        rock_img = Image.fromarray(rock)
        img.paste(rock_img, (150, 100))
        gt_box = (150, 100, 450, 300)
        return img, gt_box

    elif case_type == "dark_shiny_specimen":
        # White card with dark shiny specimen (specular hotspot)
        img = Image.new("RGB", (w, h), (225, 225, 225))
        rock = np.random.normal(loc=55, scale=10, size=(200, 300, 3)).clip(15, 100).astype(np.uint8)
        # Specular bright spot in middle of rock
        rock[80:120, 120:180] = np.random.normal(loc=230, scale=10, size=(40, 60, 3)).clip(200, 255)
        rock_img = Image.fromarray(rock)
        img.paste(rock_img, (150, 100))
        gt_box = (150, 100, 450, 300)
        return img, gt_box

    elif case_type == "light_specimen_pale_bg":
        # Pale cream background (235, 230, 220)
        img = Image.new("RGB", (w, h), (235, 230, 220))
        # Light bauxite/limestone rock (190, 175, 150) with heavy texture/grain
        rock = np.random.normal(loc=180, scale=25, size=(200, 300, 3)).clip(110, 230).astype(np.uint8)
        rock_img = Image.fromarray(rock)
        img.paste(rock_img, (150, 100))
        gt_box = (150, 100, 450, 300)
        return img, gt_box

    elif case_type == "already_fills_frame":
        # Pure texture filling whole frame
        rock = np.random.normal(loc=70, scale=15, size=(h, w, 3)).clip(20, 120).astype(np.uint8)
        return Image.fromarray(rock), (0, 0, w, h)

print("Test generator defined.")

import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scratch"))
from test_segmenter import segment_rock_specimen

cases = ["white_card_dark_specimen", "dark_shiny_specimen", "light_specimen_pale_bg", "already_fills_frame"]
for c in cases:
    im, gt = create_synthetic_test_case(c)
    crop, diag = segment_rock_specimen(im)
    print(f"\nCase: {c}")
    print(f"  GT Box: {gt}")
    print(f"  Detected Box: {diag['crop_box']}")
    print(f"  Is Segmented: {diag['is_segmented']}")
    print(f"  Quality: {diag['segmentation_quality']}")
    print(f"  Notes: {diag['notes']}")

# Uneven lighting test
w, h = 600, 400
img_uneven = Image.new("RGB", (w, h), (240, 240, 240))
draw = ImageDraw.Draw(img_uneven)
# Gradient across entire card from 250 on left to 170 on right
for x in range(w):
    val = int(250 - (x / w) * 80)
    draw.line([(x, 0), (x, h)], fill=(val, val, val))
# Add rock in center
rock = np.random.normal(loc=50, scale=10, size=(180, 260, 3)).clip(10, 80).astype(np.uint8)
img_uneven.paste(Image.fromarray(rock), (170, 110))

crop, diag = segment_rock_specimen(img_uneven)
print(f"\nCase: uneven_lighting_and_shadows")
print(f"  GT Box: (170, 110, 430, 290)")
print(f"  Detected Box: {diag['crop_box']}")
print(f"  Is Segmented: {diag['is_segmented']}")
print(f"  Quality: {diag['segmentation_quality']}")
print(f"  Notes: {diag['notes']}")
