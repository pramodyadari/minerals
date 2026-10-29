import numpy as np
from PIL import Image

path = 'data/uploads/20261028_134742_70df91e2acfb_Bituminous_Coal.jpg'
img = Image.open(path).convert('RGB')
crop_box = (760, 264, 3896, 2736)
crop_img = img.crop(crop_box)
arr = np.array(crop_img, dtype=np.float32)

lum = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]
print('Crop dimensions:', crop_img.size)
print('Mean luminance of crop:', lum.mean())
print('Min lum:', lum.min(), 'Max lum:', lum.max())
print('Percentage of pixels with lum > 170 (white card in crop corners):', (lum > 170).mean() * 100)

# If we take a tighter central crop of the rock (e.g. center 50% of the bounding box where there is NO white card)
cw = crop_box[2] - crop_box[0]
ch = crop_box[3] - crop_box[1]
inner_box = (
    crop_box[0] + int(cw * 0.2),
    crop_box[1] + int(ch * 0.2),
    crop_box[2] - int(cw * 0.2),
    crop_box[3] - int(ch * 0.2),
)
inner_img = img.crop(inner_box)
inner_arr = np.array(inner_img, dtype=np.float32)
inner_lum = 0.299 * inner_arr[:,:,0] + 0.587 * inner_arr[:,:,1] + 0.114 * inner_arr[:,:,2]
print('Inner rock crop dimensions:', inner_img.size)
print('Inner rock mean lum:', inner_lum.mean())
print('Inner rock % lum > 170:', (inner_lum > 170).mean() * 100)

