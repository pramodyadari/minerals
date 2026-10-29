import os
import sys
import glob
import numpy as np
from PIL import Image
from scipy import ndimage

def segment_rock_specimen(img: Image.Image, padding_pct: float = 0.03):
    """
    Isolates rock specimen from background card/plate.
    Returns: (cropped_img, diagnostic_dict)
    """
    orig_w, orig_h = img.size
    diagnostic = {
        "original_dimensions": [orig_w, orig_h],
        "crop_box": [0, 0, orig_w, orig_h],
        "is_segmented": False,
        "segmentation_quality": "UNCERTAIN_FALLBACK",
        "method_used": "scipy_morphological_texture",
        "foreground_area_ratio": 1.0,
        "notes": []
    }

    # Minimum size check
    if orig_w < 16 or orig_h < 16:
        diagnostic["notes"].append(f"Image too small ({orig_w}x{orig_h}); skipping segmentation.")
        return img, diagnostic

    # Downsample for robust, fast analysis
    max_dim = 512
    scale = min(1.0, max_dim / max(orig_w, orig_h))
    sw = max(16, int(orig_w * scale))
    sh = max(16, int(orig_h * scale))
    small = img.resize((sw, sh), Image.Resampling.BILINEAR)
    arr = np.array(small, dtype=np.float32)

    # 1. Border analysis: sample 6% perimeter
    bw = max(2, int(sw * 0.06))
    bh = max(2, int(sh * 0.06))
    border_mask = np.zeros((sh, sw), dtype=bool)
    border_mask[:bh, :] = True
    border_mask[-bh:, :] = True
    border_mask[:, :bw] = True
    border_mask[:, -bw:] = True

    border_pixels = arr[border_mask]
    border_mean = border_pixels.mean(axis=0) # [R, G, B]
    border_std = border_pixels.std(axis=0)
    border_lum = 0.299 * border_mean[0] + 0.587 * border_mean[1] + 0.114 * border_mean[2]
    border_std_lum = float(np.mean(border_std))

    diagnostic["border_mean_rgb"] = [round(float(x), 1) for x in border_mean]
    diagnostic["border_std_mean"] = round(border_std_lum, 2)
    diagnostic["border_luminance"] = round(float(border_lum), 1)

    # Check if border is uniform (pale card or uniform surface)
    is_uniform_border = border_std_lum < 28.0
    is_pale_card = border_lum > 165.0 and is_uniform_border

    # Color difference from border
    diff = np.linalg.norm(arr - border_mean, axis=2)

    # Gradient / texture energy
    lum = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]
    gx = ndimage.sobel(lum, axis=1)
    gy = ndimage.sobel(lum, axis=0)
    grad_mag = np.hypot(gx, gy)
    grad_smooth = ndimage.gaussian_filter(grad_mag, sigma=2.0)

    # If the image does not have a uniform border, the specimen likely fills the frame
    if not is_uniform_border:
        diagnostic["notes"].append("Border is non-uniform; specimen appears to already fill the frame.")
        return img, diagnostic

    # Foreground thresholding:
    # A rock on a pale card has either significant color/lum difference OR distinct internal texture.
    # Shadows on card have mild lum difference and virtually zero texture.
    if is_pale_card:
        # Foreground pixels differ significantly from white card
        fg_candidate = (diff > max(35.0, border_std_lum * 2.8)) | (grad_smooth > 25.0)
    else:
        # Neutral or darker uniform background
        fg_candidate = (diff > max(40.0, border_std_lum * 3.0))

    # Morphological cleanup: close small holes, remove speckles
    # 5x5 structuring element
    struct = ndimage.generate_binary_structure(2, 2)
    fg_closed = ndimage.binary_closing(fg_candidate, structure=struct, iterations=3)
    fg_cleaned = ndimage.binary_opening(fg_closed, structure=struct, iterations=2)

    # Connected components
    labeled, num_features = ndimage.label(fg_cleaned)
    if num_features == 0:
        diagnostic["notes"].append("No foreground specimen component identified.")
        return img, diagnostic

    sizes = ndimage.sum(fg_cleaned, labeled, range(1, num_features + 1))
    max_idx = int(np.argmax(sizes))
    max_size = sizes[max_idx]
    component_ratio = float(max_size / (sw * sh))

    # Reject if component is tiny (< 3% of frame) or huge (> 95% of frame)
    if component_ratio < 0.03:
        diagnostic["notes"].append(f"Largest component too small ({component_ratio:.1%}); uncertain segmentation.")
        return img, diagnostic

    if component_ratio > 0.95:
        diagnostic["notes"].append("Specimen already occupies >95% of frame; cropping unnecessary.")
        return img, diagnostic

    # Find bounding box of largest component
    target_mask = (labeled == (max_idx + 1)).astype(np.int32)
    locs = ndimage.find_objects(target_mask)
    if not locs or locs[0] is None:
        diagnostic["notes"].append("Could not locate component bounding box.")
        return img, diagnostic

    yslice, xslice = locs[0]
    # Scale coordinates back to original resolution
    x_scale = orig_w / float(sw)
    y_scale = orig_h / float(sh)

    x1 = int(xslice.start * x_scale)
    x2 = int(xslice.stop * x_scale)
    y1 = int(yslice.start * y_scale)
    y2 = int(yslice.stop * y_scale)

    # Optional conservative padding (preserve specimen boundaries)
    pad_x = int((x2 - x1) * padding_pct)
    pad_y = int((y2 - y1) * padding_pct)
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(orig_w, x2 + pad_x)
    y2 = min(orig_h, y2 + pad_y)

    crop_w = x2 - x1
    crop_h = y2 - y1
    area_ratio = float((crop_w * crop_h) / (orig_w * orig_h))

    # Quality classification
    if is_pale_card and 0.15 <= area_ratio <= 0.85:
        quality = "HIGH"
    elif 0.08 <= area_ratio <= 0.92:
        quality = "MODERATE"
    else:
        quality = "LOW"

    diagnostic["crop_box"] = [x1, y1, x2, y2]
    diagnostic["crop_dimensions"] = [crop_w, crop_h]
    diagnostic["foreground_area_ratio"] = round(area_ratio, 4)
    diagnostic["is_segmented"] = True
    diagnostic["segmentation_quality"] = quality
    diagnostic["notes"].append(f"Successfully segmented specimen ({quality} confidence, occupies {area_ratio:.1%} of frame).")

    crop_img = img.crop((x1, y1, x2, y2))
    return crop_img, diagnostic


if __name__ == "__main__":
    coal_path = "data/uploads/20261028_134742_70df91e2acfb_Bituminous_Coal.jpg"
    img = Image.open(coal_path).convert("RGB")
    crop, diag = segment_rock_specimen(img)
    print("Coal Test Diagnostic:", diag)
