import os
import glob
from PIL import Image

for sample_dir in [
    "data/train/coal",
    "data/train/manganese",
    "data/train/iron_ore",
    "data/train/bauxite",
    "data/evaluation/ood/quartz",
    "data/evaluation/ood/basalt",
    "data/evaluation/ood/sandstone",
    "data/evaluation/known/coal",
]:
    files = glob.glob(f"{sample_dir}/*.*")
    if files:
        im = Image.open(files[0])
        print(f"{sample_dir}: {len(files)} files, first={os.path.basename(files[0])}, size={im.size}, format={im.format}, info={im.info}")
