"""
AI Mineral Intelligence — Procedural Benchmark Mineral Sample Generator
Generates distinctive mineral specimen images for Coal, Manganese, Iron Ore, and Bauxite
based on authentic mineralogical visual signatures:
  1. Coal: Vitreous/dull black, carbonaceous strata, conchoidal fractures.
  2. Manganese: Steel-gray to velvety black pyrolusite, dendritic and crystalline metallic sheen.
  3. Iron Ore: Brick-red/sub-metallic hematite and banded iron formation (BIF) banding.
  4. Bauxite: Pisolitic nodular texture, reddish-brown/tan clayey lateritic matrix.
"""

import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CLASSES = ["coal", "manganese", "iron_ore", "bauxite"]
SPLITS = {
    "train": 35,
    "validation": 10,
    "test": 10
}

def create_coal_image(seed):
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    # Base dark carbonaceous tones: deep gray to jet black
    base_lum = np.random.normal(25, 8, (h, w))
    # Stratified fracture lines
    for _ in range(6):
        y_stripe = random.randint(20, h - 20)
        stripe_w = random.randint(2, 6)
        base_lum[max(0, y_stripe - stripe_w):min(h, y_stripe + stripe_w), :] += random.randint(-10, 15)
        
    base_lum = np.clip(base_lum, 5, 60).astype(np.uint8)
    
    # Slight blueish-cold metallic luster
    r = base_lum
    g = np.clip(base_lum.astype(int) + np.random.normal(0, 2, (h, w)), 0, 255).astype(np.uint8)
    b = np.clip(base_lum.astype(int) + np.random.normal(3, 3, (h, w)), 0, 255).astype(np.uint8)
    
    img_arr = np.stack([r, g, b], axis=-1)
    img = Image.fromarray(img_arr)
    # Add specular facet gleams
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(4, 10)):
        x = random.randint(20, w - 20)
        y = random.randint(20, h - 20)
        sz = random.randint(2, 6)
        draw.polygon([(x, y), (x + sz, y + sz//2), (x + sz//2, y + sz)], fill=(90, 100, 115))
        
    return img.filter(ImageFilter.SMOOTH)

def create_manganese_image(seed):
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    # Metallic steel-gray to silvery black
    base_lum = np.random.normal(65, 15, (h, w))
    # Pyrolusite botryoidal / dendritic nodules
    for _ in range(12):
        cx, cy = random.randint(20, w - 20), random.randint(20, h - 20)
        rad = random.randint(10, 35)
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_sq = (x_grid - cx)**2 + (y_grid - cy)**2
        mask = dist_sq < rad**2
        intensity = random.choice([25, -25, 40])
        base_lum[mask] = np.clip(base_lum[mask] + intensity, 10, 140)
        
    base_lum = np.clip(base_lum, 15, 140).astype(np.uint8)
    # Neutral/silvery metallic balance
    r = base_lum
    g = np.clip(base_lum.astype(int) + 2, 0, 255).astype(np.uint8)
    b = np.clip(base_lum.astype(int) + 6, 0, 255).astype(np.uint8)
    
    img = Image.fromarray(np.stack([r, g, b], axis=-1))
    return img.filter(ImageFilter.SMOOTH_MORE)

def create_iron_ore_image(seed):
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    # Hematite reddish-brown to dark rust-ochre
    r_base = np.random.normal(140, 25, (h, w))
    g_base = np.random.normal(55, 15, (h, w))
    b_base = np.random.normal(40, 12, (h, w))
    
    # Banded Iron Formation (BIF) banding
    for _ in range(8):
        y_start = random.randint(10, h - 30)
        thickness = random.randint(6, 18)
        dark_factor = random.uniform(0.4, 0.7)
        r_base[y_start:y_start+thickness, :] *= dark_factor
        g_base[y_start:y_start+thickness, :] *= dark_factor
        b_base[y_start:y_start+thickness, :] *= dark_factor
        
    r = np.clip(r_base, 30, 210).astype(np.uint8)
    g = np.clip(g_base, 15, 110).astype(np.uint8)
    b = np.clip(b_base, 10, 85).astype(np.uint8)
    
    img = Image.fromarray(np.stack([r, g, b], axis=-1))
    return img.filter(ImageFilter.SMOOTH)

def create_bauxite_image(seed):
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    # Tan / light brownish-orange lateritic clay matrix
    r_base = np.random.normal(195, 18, (h, w))
    g_base = np.random.normal(135, 18, (h, w))
    b_base = np.random.normal(85, 15, (h, w))
    
    img = Image.fromarray(np.stack([
        np.clip(r_base, 80, 240).astype(np.uint8),
        np.clip(g_base, 50, 180).astype(np.uint8),
        np.clip(b_base, 30, 130).astype(np.uint8)
    ], axis=-1))
    
    # Pisolitic nodules (circular spherical grains typical of bauxite)
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(25, 45)):
        cx, cy = random.randint(10, w - 10), random.randint(10, h - 10)
        r = random.randint(3, 12)
        fill_col = (
            random.randint(120, 160),
            random.randint(70, 95),
            random.randint(40, 60)
        )
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=fill_col, outline=(90, 50, 30))
        
    return img.filter(ImageFilter.SMOOTH)

GENERATORS = {
    "coal": create_coal_image,
    "manganese": create_manganese_image,
    "iron_ore": create_iron_ore_image,
    "bauxite": create_bauxite_image
}

def generate_all_samples():
    base_dirs = ["data", os.path.join("ai", "dataset")]
    total_created = 0
    
    for split_name, count in SPLITS.items():
        for cls_name in CLASSES:
            gen_func = GENERATORS[cls_name]
            for i in range(count):
                seed = hash(f"{split_name}_{cls_name}_{i}") & 0x7FFFFFFF
                img = gen_func(seed)
                filename = f"{cls_name}_{split_name}_{i:03d}.jpg"
                
                # Save to both data/ and ai/dataset/
                for b in base_dirs:
                    target_dir = os.path.join(b, split_name, cls_name)
                    os.makedirs(target_dir, exist_ok=True)
                    img.save(os.path.join(target_dir, filename), "JPEG", quality=92)
                total_created += 1
                
    print(f"Successfully generated {total_created} calibrated mineral images across 4 classes and 3 splits.")

if __name__ == "__main__":
    generate_all_samples()
