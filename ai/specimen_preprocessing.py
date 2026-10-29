"""
AI Mineral Specimen Preprocessing & Isolation Utility
Isolates rock specimens from background cards, plates, and photographic framing
for mineral specimen classification and OOD manifold distance evaluation.

Key Capabilities:
1. Baseline vs. Cropped Specimen: Generates both untouched baseline and candidate crop.
2. Illumination Invariance: Fits planar background models to perimeter pixels to handle
   lighting gradients and directional shadows.
3. Texture & Chromaticity Discrimination: Differentiates specimen rock texture from smooth
   cast shadows on white paper cards (avoiding assuming every non-white pixel is rock).
4. Optional OpenCV GrabCut: Leverages cv2.grabCut when installed, with seamless fallback
   to SciPy morphological & texture segmentation.
5. Conservative Boundary Preservation: Preserves natural mineral boundaries and texture
   with safety margins and hole filling.
6. Graceful Degradation: Reverts to original image if isolation is uncertain, and safely
   handles tiny (<16x16), oversized (>8192x8192), or corrupt inputs.
"""

import os
import io
import math
from typing import Tuple, Dict, Any, Optional, Union
import numpy as np
from PIL import Image
from scipy import ndimage

# Check optional OpenCV availability
try:
    import cv2
    _OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    _OPENCV_AVAILABLE = False


def is_opencv_available() -> bool:
    """Returns True if OpenCV (cv2) is installed and importable."""
    return _OPENCV_AVAILABLE


def preprocess_image_input(image_input: Union[str, bytes, Image.Image, np.ndarray]) -> Tuple[Optional[Image.Image], Optional[str]]:
    """
    Normalizes various input formats into a valid PIL RGB Image.
    Returns (pil_image, error_message).
    """
    if image_input is None:
        return None, "Input image is None."

    try:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return None, f"File not found: {image_input}"
            with open(image_input, "rb") as fp:
                data = fp.read()
            if len(data) == 0:
                return None, "File is empty (0 bytes)."
            raw_img = Image.open(io.BytesIO(data))
        elif isinstance(image_input, bytes):
            if len(image_input) == 0:
                return None, "Image bytes buffer is empty."
            raw_img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            raw_img = image_input
        elif isinstance(image_input, np.ndarray):
            if image_input.size == 0:
                return None, "NumPy image array is empty."
            raw_img = Image.fromarray(image_input.astype(np.uint8))
        else:
            return None, f"Unsupported input type: {type(image_input)}"

        # Access primary frame for multi-frame formats (e.g. MPO)
        if hasattr(raw_img, "seek"):
            try:
                raw_img.seek(0)
            except Exception:
                pass

        w, h = raw_img.size
        if w < 16 or h < 16:
            return None, f"Image dimensions ({w}x{h}) too small. Minimum resolution is 16x16."
        if w > 8192 or h > 8192:
            return None, f"Image dimensions ({w}x{h}) exceed maximum allowed dimension (8192x8192)."

        return raw_img.convert("RGB"), None

    except Image.DecompressionBombError:
        return None, "Image exceeds maximum safe decompression limit (decompression bomb risk)."
    except Exception as exc:
        return None, f"Failed to decode image: {str(exc)}"


def isolate_specimen(
    image_input: Union[str, bytes, Image.Image, np.ndarray],
    padding_pct: float = 0.04,
    use_grabcut_if_available: bool = True,
    fallback_on_uncertain: bool = True
) -> Dict[str, Any]:
    """
    Isolates a mineral specimen from background support cards/plates.
    
    Returns a dictionary containing:
    - original_image: PIL RGB image of untouched baseline.
    - candidate_crop: PIL RGB image of segmented specimen crop (or original if uncertain).
    - is_segmented: bool, True if specimen was confidently isolated from background.
    - segmentation_quality: "HIGH", "MODERATE", "LOW", or "UNCERTAIN_FALLBACK".
    - crop_box: [x1, y1, x2, y2] bounding box coordinates on original image.
    - original_dimensions: [width, height].
    - crop_dimensions: [width, height].
    - foreground_area_ratio: float, area of candidate crop relative to full image.
    - method_used: str, algorithm utilized ("opencv_grabcut", "scipy_morphological_texture", "original_baseline_passthrough").
    - border_diagnostics: dict with border statistics and illumination fit.
    - notes: list of diagnostic observations.
    - opencv_available: bool.
    """
    orig_img, err = preprocess_image_input(image_input)
    if err or orig_img is None:
        return {
            "status": "ERROR",
            "message": err or "Invalid image input",
            "original_image": None,
            "candidate_crop": None,
            "is_segmented": False,
            "segmentation_quality": "INVALID_INPUT",
            "crop_box": [0, 0, 0, 0],
            "original_dimensions": [0, 0],
            "crop_dimensions": [0, 0],
            "foreground_area_ratio": 0.0,
            "method_used": "none",
            "border_diagnostics": {},
            "notes": [f"Input failure: {err}"],
            "opencv_available": _OPENCV_AVAILABLE
        }

    orig_w, orig_h = orig_img.size
    diagnostic = {
        "status": "SUCCESS",
        "message": "Processed successfully",
        "original_image": orig_img,
        "candidate_crop": orig_img,
        "is_segmented": False,
        "segmentation_quality": "UNCERTAIN_FALLBACK",
        "crop_box": [0, 0, orig_w, orig_h],
        "original_dimensions": [orig_w, orig_h],
        "crop_dimensions": [orig_w, orig_h],
        "foreground_area_ratio": 1.0,
        "method_used": "original_baseline_passthrough",
        "border_diagnostics": {},
        "notes": [],
        "opencv_available": _OPENCV_AVAILABLE
    }

    # 1. Downsample for fast, noise-tolerant spatial and gradient analysis
    max_dim = 512
    scale = min(1.0, max_dim / float(max(orig_w, orig_h)))
    sw = max(16, int(orig_w * scale))
    sh = max(16, int(orig_h * scale))
    small = orig_img.resize((sw, sh), Image.Resampling.BILINEAR)
    small_arr = np.array(small, dtype=np.float32)

    # 2. Border Sampling & Planar Illumination Background Modeling
    bw = max(2, int(sw * 0.07))
    bh = max(2, int(sh * 0.07))

    # Identify border pixels (outer 7% perimeter band)
    border_mask = np.zeros((sh, sw), dtype=bool)
    border_mask[:bh, :] = True
    border_mask[-bh:, :] = True
    border_mask[:, :bw] = True
    border_mask[:, -bw:] = True

    border_rgb = small_arr[border_mask]
    border_mean_rgb = border_rgb.mean(axis=0)
    border_std_rgb = border_rgb.std(axis=0)
    border_mean_lum = float(0.299 * border_mean_rgb[0] + 0.587 * border_mean_rgb[1] + 0.114 * border_mean_rgb[2])
    border_std_lum = float(np.mean(border_std_rgb))

    # Center sample (inner 50% box) to check if specimen already fills the whole frame
    center_rgb = small_arr[int(sh * 0.25):int(sh * 0.75), int(sw * 0.25):int(sw * 0.75)].reshape(-1, 3)
    center_mean_rgb = center_rgb.mean(axis=0)
    center_to_border_divergence = float(np.linalg.norm(center_mean_rgb - border_mean_rgb))

    # Fit 1st-order planar illumination model to perimeter: lum = a*x + b*y + c
    lum = 0.299 * small_arr[:, :, 0] + 0.587 * small_arr[:, :, 1] + 0.114 * small_arr[:, :, 2]
    border_coords = []
    border_lums = []
    step = max(1, int(len(border_rgb) // 500))  # subsample for speed
    y_idxs, x_idxs = np.where(border_mask)
    for idx in range(0, len(y_idxs), step):
        border_coords.append([x_idxs[idx], y_idxs[idx], 1.0])
        border_lums.append(lum[y_idxs[idx], x_idxs[idx]])

    A = np.array(border_coords, dtype=np.float32)
    b_vec = np.array(border_lums, dtype=np.float32)
    try:
        plane, _, _, _ = np.linalg.lstsq(A, b_vec, rcond=None)
        xx, yy = np.meshgrid(np.arange(sw), np.arange(sh))
        fitted_bg = plane[0] * xx + plane[1] * yy + plane[2]
        border_residuals = np.abs(lum[border_mask] - fitted_bg[border_mask])
        border_fit_residual_std = float(border_residuals.std())
    except Exception:
        fitted_bg = np.full((sh, sw), border_mean_lum, dtype=np.float32)
        border_fit_residual_std = border_std_lum

    diagnostic["border_diagnostics"] = {
        "border_mean_rgb": [round(float(x), 2) for x in border_mean_rgb],
        "border_std_mean": round(border_std_lum, 2),
        "border_mean_luminance": round(border_mean_lum, 2),
        "border_fit_residual_std": round(border_fit_residual_std, 2),
        "center_to_border_divergence": round(center_to_border_divergence, 2)
    }

    # 3. Decision Gate: Does this image have a distinct background card, or is it already filling the frame?
    is_pale_card = border_mean_lum >= 155.0 and border_fit_residual_std <= 32.0
    is_dark_neutral_plate = border_mean_lum < 155.0 and border_fit_residual_std <= 18.0 and center_to_border_divergence > 35.0

    if not is_pale_card and not is_dark_neutral_plate:
        # Border has high non-planar variance or center has virtually identical color to border
        diagnostic["notes"].append(
            "Perimeter border is either non-uniform or identical to center; specimen appears to already fill the frame."
        )
        return diagnostic

    if center_to_border_divergence < 22.0:
        diagnostic["notes"].append(
            f"Center-to-border contrast ({center_to_border_divergence:.1f}) is low; whole image appears homogeneous."
        )
        return diagnostic

    # 4. Foreground Specimen Candidate Mask
    # Compute divergence from fitted background
    bg_lum_diff = np.abs(fitted_bg - lum)

    # Compute high-frequency texture gradient (Sobel magnitude)
    # Distinguishes genuine rock texture from smooth cast paper shadows
    gx = ndimage.sobel(lum, axis=1)
    gy = ndimage.sobel(lum, axis=0)
    grad_mag = np.hypot(gx, gy)
    grad_smooth = ndimage.gaussian_filter(grad_mag, sigma=1.5)

    # Chromatic difference from background
    color_diff = np.linalg.norm(small_arr - border_mean_rgb, axis=2)

    # Foreground thresholding
    if is_pale_card:
        # Dark or colored specimen on pale/white card:
        # Significant luminance drop OR distinct texture with chromatic difference
        min_contrast = max(28.0, border_fit_residual_std * 2.8)
        is_fg = (bg_lum_diff > min_contrast) | ((grad_smooth > 22.0) & (color_diff > 18.0))
    else:
        # Specimen on dark/neutral plate
        min_contrast = max(35.0, border_fit_residual_std * 3.0)
        is_fg = (color_diff > min_contrast) | (grad_smooth > 25.0)

    # 5. Morphological Structuring: Fill internal cracks/specular spots and remove dust
    struct = ndimage.generate_binary_structure(2, 2)
    fg_closed = ndimage.binary_closing(is_fg, structure=struct, iterations=3)
    fg_cleaned = ndimage.binary_opening(fg_closed, structure=struct, iterations=2)

    # 6. Connected Component Analysis
    labeled, num_features = ndimage.label(fg_cleaned)
    if num_features == 0:
        diagnostic["notes"].append("No foreground specimen component identified.")
        return diagnostic

    sizes = ndimage.sum(fg_cleaned, labeled, range(1, num_features + 1))
    max_idx = int(np.argmax(sizes))
    max_size = float(sizes[max_idx])
    component_ratio = max_size / float(sw * sh)

    if component_ratio < 0.02:
        diagnostic["notes"].append(
            f"Largest foreground component occupies only {component_ratio:.1%} of frame; uncertain segmentation."
        )
        return diagnostic

    if component_ratio > 0.94:
        diagnostic["notes"].append(
            f"Foreground component occupies {component_ratio:.1%} of frame; already filling frame."
        )
        return diagnostic

    # Candidate bounding box from connected component
    target_mask = (labeled == (max_idx + 1)).astype(np.int32)
    locs = ndimage.find_objects(target_mask)
    if not locs or locs[0] is None:
        diagnostic["notes"].append("Could not extract bounding box.")
        return diagnostic

    yslice, xslice = locs[0]
    sub_x1, sub_x2 = xslice.start, xslice.stop
    sub_y1, sub_y2 = yslice.start, yslice.stop

    method_used = "scipy_morphological_texture"

    # 7. Optional OpenCV GrabCut Refinement (when available and enabled)
    if use_grabcut_if_available and _OPENCV_AVAILABLE:
        try:
            # Prepare GrabCut initialization with rectangle
            small_bgr = cv2.cvtColor(small_arr.astype(np.uint8), cv2.COLOR_RGB2BGR)
            gc_mask = np.zeros((sh, sw), dtype=np.uint8)
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)

            # Define rect with 2px inset/bounds
            rect_x = max(0, sub_x1)
            rect_y = max(0, sub_y1)
            rect_w = min(sw - rect_x, sub_x2 - sub_x1)
            rect_h = min(sh - rect_y, sub_y2 - sub_y1)

            if rect_w > 10 and rect_h > 10:
                cv2.grabCut(
                    small_bgr,
                    gc_mask,
                    (rect_x, rect_y, rect_w, rect_h),
                    bgd_model,
                    fgd_model,
                    iterCount=3,
                    mode=cv2.GC_INIT_WITH_RECT
                )
                gc_fg = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 1, 0).astype(np.int32)
                gc_labeled, gc_num = ndimage.label(gc_fg)
                if gc_num > 0:
                    gc_sizes = ndimage.sum(gc_fg, gc_labeled, range(1, gc_num + 1))
                    gc_max_idx = int(np.argmax(gc_sizes))
                    gc_locs = ndimage.find_objects((gc_labeled == (gc_max_idx + 1)).astype(np.int32))
                    if gc_locs and gc_locs[0] is not None:
                        yslice_gc, xslice_gc = gc_locs[0]
                        sub_x1, sub_x2 = xslice_gc.start, xslice_gc.stop
                        sub_y1, sub_y2 = yslice_gc.start, yslice_gc.stop
                        method_used = "opencv_grabcut"
        except Exception as gc_exc:
            diagnostic["notes"].append(f"OpenCV GrabCut warning ({str(gc_exc)}); used SciPy fallback.")
            method_used = "scipy_morphological_texture"
    elif not _OPENCV_AVAILABLE:
        diagnostic["notes"].append("OpenCV not installed in environment; evaluated using SciPy morphological texture segmentation.")

    # 8. Coordinate Mapping & Conservative Padding
    x_scale = orig_w / float(sw)
    y_scale = orig_h / float(sh)

    raw_x1 = int(sub_x1 * x_scale)
    raw_x2 = int(sub_x2 * x_scale)
    raw_y1 = int(sub_y1 * y_scale)
    raw_y2 = int(sub_y2 * y_scale)

    # Conservative padding: preserve specimen outer margins and mineral edges
    bw_crop = raw_x2 - raw_x1
    bh_crop = raw_y2 - raw_y1
    pad_x = int(bw_crop * padding_pct)
    pad_y = int(bh_crop * padding_pct)

    x1 = max(0, raw_x1 - pad_x)
    y1 = max(0, raw_y1 - pad_y)
    x2 = min(orig_w, raw_x2 + pad_x)
    y2 = min(orig_h, raw_y2 + pad_y)

    crop_w = x2 - x1
    crop_h = y2 - y1
    area_ratio = float((crop_w * crop_h) / (orig_w * orig_h))

    # Evaluate Segmentation Quality
    if 0.12 <= area_ratio <= 0.85 and (is_pale_card or is_dark_neutral_plate):
        quality = "HIGH"
    elif 0.05 <= area_ratio <= 0.92:
        quality = "MODERATE"
    else:
        quality = "LOW"

    candidate_crop = orig_img.crop((x1, y1, x2, y2))

    diagnostic["candidate_crop"] = candidate_crop
    diagnostic["crop_box"] = [x1, y1, x2, y2]
    diagnostic["crop_dimensions"] = [crop_w, crop_h]
    diagnostic["foreground_area_ratio"] = round(area_ratio, 4)
    diagnostic["is_segmented"] = True
    diagnostic["segmentation_quality"] = quality
    diagnostic["method_used"] = method_used
    diagnostic["notes"].append(
        f"Specimen isolated successfully ({quality} quality, method: {method_used}, area ratio: {area_ratio:.1%})."
    )

    return diagnostic


def prepare_production_tensor(
    pil_image: Image.Image,
    target_size: Tuple[int, int] = (224, 224)
) -> np.ndarray:
    """
    Constructs normalized (C, H, W) float32 tensor matching exact production pipeline:
    ImageNet mean [0.485, 0.456, 0.406] and std [0.229, 0.224, 0.225].
    """
    resized = pil_image.convert("RGB").resize(target_size, Image.Resampling.BILINEAR)
    arr = np.array(resized, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    norm = (arr - mean) / std
    return np.transpose(norm, (2, 0, 1))

