import numpy as np
from PIL import Image

im1 = np.array(Image.open("data/evaluation/known/coal/test_coal_test_000.jpg"))
im2 = np.array(Image.open("data/test/coal/coal_test_000.jpg"))

diff = np.abs(im1.astype(float) - im2.astype(float))
print(f"Max pixel difference: {diff.max()}, Mean pixel difference: {diff.mean()}")
