"""
AI Mineral Intelligence — Procedural Out-of-Distribution & Evaluation Set Generator
Generates:
  1. OOD rock specimens (Quartz, Granite, Limestone, Sandstone, Basalt)
  2. Copies or creates held-out validation images from the 4 supported classes (Coal, Manganese, Iron Ore, Bauxite)
  3. Evaluates feature distances, selects rejection threshold, and measures FRR/FAR.
"""

import os
import random
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OOD_CLASSES = ["quartz", "granite", "limestone", "sandstone", "basalt"]
KNOWN_CLASSES = ["coal", "manganese", "iron_ore", "bauxite"]

def create_quartz_image(seed):
    """
    Quartz (SiO2): Translucent to milky-white, vitreous luster, conchoidal fractures,
    sharp hexagonal crystal facets, high luminance with low saturation.
    """
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    # Milky white / vitreous base with subtle crystal gradients
    base = np.random.normal(232, 8, (h, w))
    
    # Crystalline fracture planes
    for _ in range(random.randint(6, 12)):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        rr, cc = np.ogrid[:h, :w]
        dist = np.abs((y2 - y1)*cc - (x2 - x1)*rr + x2*y1 - y2*x1) / (np.hypot(y2 - y1, x2 - x1) + 1e-5)
        base[dist < random.randint(2, 5)] += random.randint(-22, 18)
        
    base = np.clip(base, 175, 255).astype(np.uint8)
    r = base
    g = np.clip(base.astype(int) + np.random.normal(0, 2, (h, w)), 0, 255).astype(np.uint8)
    b = np.clip(base.astype(int) + np.random.normal(3, 2, (h, w)), 0, 255).astype(np.uint8)
    
    im = Image.fromarray(np.stack([r, g, b], axis=-1))
    draw = ImageDraw.Draw(im)
    # Hexagonal facets and vitreous gleams
    for _ in range(random.randint(6, 14)):
        x = random.randint(20, w - 20)
        y = random.randint(20, h - 20)
        sz = random.randint(8, 26)
        draw.polygon([(x, y), (x + sz, y - sz//3), (x + sz*1.2, y + sz), (x, y + sz*0.8)], 
                     fill=(248, 250, 255), outline=(185, 195, 205))
    return im.filter(ImageFilter.SMOOTH)

def create_granite_image(seed):
    """
    Granite: Phaneritic felsic igneous rock with speckled salt-and-pepper texture:
    pinkish orthoclase feldspar, white plagioclase, glassy quartz, and black biotite/hornblende.
    """
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    r = np.random.normal(188, 16, (h, w))
    g = np.random.normal(172, 16, (h, w))
    b = np.random.normal(162, 16, (h, w))
    im = Image.fromarray(np.stack([np.clip(r,0,255).astype(np.uint8),
                                  np.clip(g,0,255).astype(np.uint8),
                                  np.clip(b,0,255).astype(np.uint8)], axis=-1))
    draw = ImageDraw.Draw(im)
    # Biotite mica flakes (black/dark brown)
    for _ in range(random.randint(140, 220)):
        x, y = random.randint(4, w - 4), random.randint(4, h - 4)
        sz = random.randint(1, 4)
        draw.ellipse([(x-sz, y-sz), (x+sz, y+sz)], fill=(28, 28, 32))
    # Potassium feldspar grains (pinkish-tan)
    for _ in range(random.randint(70, 110)):
        x, y = random.randint(4, w - 4), random.randint(4, h - 4)
        sz = random.randint(2, 6)
        draw.ellipse([(x-sz, y-sz), (x+sz, y+sz)], fill=(218, 155, 142))
    # Translucent quartz patches
    for _ in range(random.randint(40, 80)):
        x, y = random.randint(4, w - 4), random.randint(4, h - 4)
        sz = random.randint(2, 5)
        draw.ellipse([(x-sz, y-sz), (x+sz, y+sz)], fill=(238, 238, 242))
    return im.filter(ImageFilter.SMOOTH)

def create_limestone_image(seed):
    """
    Limestone (CaCO3): Fine-grained micritic carbonate rock, pale buff/cream/light gray,
    uniform sedimentary matrix with subtle horizontal bedding laminae.
    """
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    r = np.random.normal(208, 9, (h, w))
    g = np.random.normal(200, 9, (h, w))
    b = np.random.normal(182, 9, (h, w))
    for _ in range(5):
        y = random.randint(15, h - 15)
        th = random.randint(2, 7)
        factor = random.uniform(0.92, 1.05)
        r[max(0, y-th):min(h, y+th), :] *= factor
        g[max(0, y-th):min(h, y+th), :] *= factor
        b[max(0, y-th):min(h, y+th), :] *= factor
    im = Image.fromarray(np.stack([np.clip(r,0,255).astype(np.uint8),
                                  np.clip(g,0,255).astype(np.uint8),
                                  np.clip(b,0,255).astype(np.uint8)], axis=-1))
    return im.filter(ImageFilter.SMOOTH)

def create_sandstone_image(seed):
    """
    Sandstone: Arenaceous sedimentary rock composed of sand-sized quartz grains,
    medium yellowish-ochre or buff tan, granular sandpaper-like gritty texture.
    """
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    r = np.random.normal(195, 14, (h, w))
    g = np.random.normal(160, 14, (h, w))
    b = np.random.normal(110, 14, (h, w))
    # Gritty fine grain variation
    grain = np.random.normal(0, 15, (h, w))
    r = np.clip(r + grain, 0, 255).astype(np.uint8)
    g = np.clip(g + grain, 0, 255).astype(np.uint8)
    b = np.clip(b + grain * 0.8, 0, 255).astype(np.uint8)
    im = Image.fromarray(np.stack([r, g, b], axis=-1))
    return im.filter(ImageFilter.SMOOTH)

def create_basalt_image(seed):
    """
    Basalt: Dark aphanitic extrusive volcanic rock, fine-grained dark gray/charcoal,
    subtle microvesicular voids, noticeably distinct from metallic manganese or coal.
    """
    random.seed(seed)
    np.random.seed(seed)
    w, h = 224, 224
    
    lum = np.random.normal(52, 9, (h, w))
    r = np.clip(lum, 10, 100).astype(np.uint8)
    g = np.clip(lum + np.random.normal(0, 2, (h, w)), 10, 100).astype(np.uint8)
    b = np.clip(lum + np.random.normal(2, 2, (h, w)), 10, 100).astype(np.uint8)
    im = Image.fromarray(np.stack([r, g, b], axis=-1))
    draw = ImageDraw.Draw(im)
    # Vesicular micropores
    for _ in range(random.randint(30, 60)):
        x, y = random.randint(10, w - 10), random.randint(10, h - 10)
        sz = random.randint(1, 3)
        draw.ellipse([(x-sz, y-sz), (x+sz, y+sz)], fill=(15, 15, 18))
    return im.filter(ImageFilter.SMOOTH)

OOD_GENERATORS = {
    "quartz": create_quartz_image,
    "granite": create_granite_image,
    "limestone": create_limestone_image,
    "sandstone": create_sandstone_image,
    "basalt": create_basalt_image
}

def build_evaluation_dataset(base_dir="data/evaluation", samples_per_ood=12):
    os.makedirs(base_dir, exist_ok=True)
    manifest = {"known": {}, "ood": {}}
    
    # 1. Gather known samples from validation and test splits
    for cls in KNOWN_CLASSES:
        out_dir = os.path.join(base_dir, "known", cls)
        os.makedirs(out_dir, exist_ok=True)
        count = 0
        for split in ["validation", "test"]:
            split_dir = os.path.join("data", split, cls)
            if os.path.exists(split_dir):
                for fname in os.listdir(split_dir):
                    if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                        src = os.path.join(split_dir, fname)
                        dst = os.path.join(out_dir, f"{split}_{fname}")
                        # Copy
                        im = Image.open(src)
                        im.save(dst)
                        count += 1
        manifest["known"][cls] = count

    # 2. Generate OOD samples
    for ood_cls, gen_func in OOD_GENERATORS.items():
        out_dir = os.path.join(base_dir, "ood", ood_cls)
        os.makedirs(out_dir, exist_ok=True)
        for i in range(samples_per_ood):
            seed = hash(f"ood_eval_{ood_cls}_{i}") & 0x7FFFFFFF
            im = gen_func(seed)
            filename = f"{ood_cls}_{i:03d}.jpg"
            im.save(os.path.join(out_dir, filename), "JPEG", quality=92)
        manifest["ood"][ood_cls] = samples_per_ood

    manifest_path = os.path.join(base_dir, "manifest.json")
    with open(manifest_path, "w") as fp:
        json.dump(manifest, fp, indent=2)
    print(f"Generated evaluation dataset: {manifest}")
    return manifest

if __name__ == "__main__":
    build_evaluation_dataset()
