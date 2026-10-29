import glob
import numpy as np
import torch
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import load_and_preprocess

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()

# Let's see all submodules in features
# Block 1: 0 to 6 (MaxPool at 6)
# Block 2: 7 to 13 (MaxPool at 13)
# Block 3: 14 to 20 (MaxPool at 20)
# Block 4: 21 to 27 (AdaptiveAvgPool at 27)

def get_layer_features(img_path):
    t = load_and_preprocess(img_path)
    with torch.no_grad():
        x = t
        acts = {}
        for idx, layer in enumerate(m.features):
            x = layer(x)
            if idx in [6, 13, 20, 27]: # pooling layers
                acts[f"pool_{idx}"] = torch.flatten(x, 1).squeeze().numpy()
    return acts

bauxite_files = glob.glob("data/test/bauxite/*.*")
sandstone_files = glob.glob("data/evaluation/ood/sandstone/*.*")

b_acts = [get_layer_features(f) for f in bauxite_files]
s_acts = [get_layer_features(f) for f in sandstone_files]

for pool_name in ["pool_6", "pool_13", "pool_20", "pool_27"]:
    b_mat = np.array([a[pool_name] for a in b_acts])
    s_mat = np.array([a[pool_name] for a in s_acts])
    b_mean = np.mean(b_mat, axis=0)
    
    # Cosine distance from b_mean
    b_cos = [1.0 - np.dot(v, b_mean)/(np.linalg.norm(v)*np.linalg.norm(b_mean)) for v in b_mat]
    s_cos = [1.0 - np.dot(v, b_mean)/(np.linalg.norm(v)*np.linalg.norm(b_mean)) for v in s_mat]
    
    print(f"Layer {pool_name} (dim {len(b_mean)}):")
    print(f"  Bauxite Cos Dist: min={min(b_cos):.6f}, max={max(b_cos):.6f}")
    print(f"  Sandstone Cos Dist: min={min(s_cos):.6f}, max={max(s_cos):.6f}")
