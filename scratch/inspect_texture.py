import glob
import numpy as np
from PIL import Image
from scipy.ndimage import laplace

def get_stats(img_path):
    im = Image.open(img_path).convert("RGB")
    arr = np.array(im, dtype=np.float32)
    gray = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]
    
    # Laplacian variance (sharpness / fine texture / roughness)
    lap = laplace(gray)
    lap_var = np.var(lap)
    
    # Color ratios
    r_mean = arr[:,:,0].mean()
    g_mean = arr[:,:,1].mean()
    b_mean = arr[:,:,2].mean()
    
    rg_ratio = r_mean / (g_mean + 1e-5)
    rb_ratio = r_mean / (b_mean + 1e-5)
    
    # Spatial gradient
    gx, gy = np.gradient(gray)
    grad_norm = np.mean(np.sqrt(gx**2 + gy**2))
    
    return {
        "r_mean": r_mean,
        "g_mean": g_mean,
        "b_mean": b_mean,
        "std": np.std(gray),
        "lap_var": lap_var,
        "grad_norm": grad_norm,
        "rg_ratio": rg_ratio,
        "rb_ratio": rb_ratio
    }

print("=== COAL vs BASALT ===")
coal_files = glob.glob("data/train/coal/*.*") + glob.glob("data/test/coal/*.*")
basalt_files = glob.glob("data/evaluation/ood/basalt/*.*")

coal_stats = [get_stats(f) for f in coal_files]
basalt_stats = [get_stats(f) for f in basalt_files]

print(f"Coal (N={len(coal_stats)}):")
print(f"  R mean: {np.mean([s['r_mean'] for s in coal_stats]):.1f} +- {np.std([s['r_mean'] for s in coal_stats]):.1f}")
print(f"  G mean: {np.mean([s['g_mean'] for s in coal_stats]):.1f} +- {np.std([s['g_mean'] for s in coal_stats]):.1f}")
print(f"  B mean: {np.mean([s['b_mean'] for s in coal_stats]):.1f} +- {np.std([s['b_mean'] for s in coal_stats]):.1f}")
print(f"  Laplacian Var: {np.mean([s['lap_var'] for s in coal_stats]):.1f} +- {np.std([s['lap_var'] for s in coal_stats]):.1f}")
print(f"  Grad Norm: {np.mean([s['grad_norm'] for s in coal_stats]):.1f} +- {np.std([s['grad_norm'] for s in coal_stats]):.1f}")

print(f"\nBasalt (N={len(basalt_stats)}):")
print(f"  R mean: {np.mean([s['r_mean'] for s in basalt_stats]):.1f} +- {np.std([s['r_mean'] for s in basalt_stats]):.1f}")
print(f"  G mean: {np.mean([s['g_mean'] for s in basalt_stats]):.1f} +- {np.std([s['g_mean'] for s in basalt_stats]):.1f}")
print(f"  B mean: {np.mean([s['b_mean'] for s in basalt_stats]):.1f} +- {np.std([s['b_mean'] for s in basalt_stats]):.1f}")
print(f"  Laplacian Var: {np.mean([s['lap_var'] for s in basalt_stats]):.1f} +- {np.std([s['lap_var'] for s in basalt_stats]):.1f}")
print(f"  Grad Norm: {np.mean([s['grad_norm'] for s in basalt_stats]):.1f} +- {np.std([s['grad_norm'] for s in basalt_stats]):.1f}")

print("\n=== BAUXITE vs SANDSTONE ===")
bauxite_files = glob.glob("data/train/bauxite/*.*") + glob.glob("data/test/bauxite/*.*")
sandstone_files = glob.glob("data/evaluation/ood/sandstone/*.*")

bauxite_stats = [get_stats(f) for f in bauxite_files]
sandstone_stats = [get_stats(f) for f in sandstone_files]

print(f"Bauxite (N={len(bauxite_stats)}):")
print(f"  R mean: {np.mean([s['r_mean'] for s in bauxite_stats]):.1f} +- {np.std([s['r_mean'] for s in bauxite_stats]):.1f}")
print(f"  G mean: {np.mean([s['g_mean'] for s in bauxite_stats]):.1f} +- {np.std([s['g_mean'] for s in bauxite_stats]):.1f}")
print(f"  B mean: {np.mean([s['b_mean'] for s in bauxite_stats]):.1f} +- {np.std([s['b_mean'] for s in bauxite_stats]):.1f}")
print(f"  Laplacian Var: {np.mean([s['lap_var'] for s in bauxite_stats]):.1f} +- {np.std([s['lap_var'] for s in bauxite_stats]):.1f}")
print(f"  Grad Norm: {np.mean([s['grad_norm'] for s in bauxite_stats]):.1f} +- {np.std([s['grad_norm'] for s in bauxite_stats]):.1f}")

print(f"\nSandstone (N={len(sandstone_stats)}):")
print(f"  R mean: {np.mean([s['r_mean'] for s in sandstone_stats]):.1f} +- {np.std([s['r_mean'] for s in sandstone_stats]):.1f}")
print(f"  G mean: {np.mean([s['g_mean'] for s in sandstone_stats]):.1f} +- {np.std([s['g_mean'] for s in sandstone_stats]):.1f}")
print(f"  B mean: {np.mean([s['b_mean'] for s in sandstone_stats]):.1f} +- {np.std([s['b_mean'] for s in sandstone_stats]):.1f}")
print(f"  Laplacian Var: {np.mean([s['lap_var'] for s in sandstone_stats]):.1f} +- {np.std([s['lap_var'] for s in sandstone_stats]):.1f}")
print(f"  Grad Norm: {np.mean([s['grad_norm'] for s in sandstone_stats]):.1f} +- {np.std([s['grad_norm'] for s in sandstone_stats]):.1f}")
