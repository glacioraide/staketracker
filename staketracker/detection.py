"""Image-based stake detection using weighted Sobel edge filtering.

This module provides the core computer-vision pipeline:

1. Load a grayscale image.
2. Enhance local contrast with CLAHE and compute a weighted Sobel gradient.
3. Threshold the gradient magnitude to isolate high-contrast pixels inside
   a region of interest (ROI).
4. Measure the vertical extent of detected pixels to estimate the stake height.

The module also exposes helpers for parameter optimisation (``optimize_params``)
and for reading EXIF capture dates from JPEG files (``read_image_date``).
"""

from datetime import datetime

import cv2
import numpy as np
import piexif
from scipy.optimize import differential_evolution

# ---------------------------------------------------------------------------
# Image I/O
# ---------------------------------------------------------------------------


def load_gray(image_path: str) -> np.ndarray:
    """Load an image from disk and convert it to grayscale.

    Parameters
    ----------
    image_path : str
        Path to the input image file.

    Returns
    -------
    numpy.ndarray
        Two-dimensional grayscale image.

    Raises
    ------
    AssertionError
        Raised when the image cannot be loaded from ``image_path``.
    """
    img = cv2.imread(image_path)
    assert img is not None, f"Cannot load: {image_path}"
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------------------
# Edge enhancement
#
# apply_weighted_sobel() chains three steps, each available on its own so that
# notebooks/pipeline_step_by_step.ipynb can show the intermediate images:
# enhance_contrast() -> weighted_gradient() -> normalize_gradient().
# ---------------------------------------------------------------------------


def enhance_contrast(gray: np.ndarray, blur_size: int = 5, clahe_clip: float = 3.0, clahe_tile: int = 8) -> np.ndarray:
    """Blur the image, then enhance local contrast with CLAHE.

    Parameters
    ----------
    gray : numpy.ndarray
        Input grayscale image.
    blur_size : int, default 5
        Gaussian blur kernel size, removes sensor noise.
    clahe_clip : float, default 3.0
        Clip limit used by CLAHE.
    clahe_tile : int, default 8
        Tile grid size used by CLAHE.  Values below 2 are rejected by OpenCV.

    Returns
    -------
    numpy.ndarray
        Enhanced 8-bit grayscale image.
    """
    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))
    return clahe.apply(blurred)


def weighted_gradient(img: np.ndarray, wx: float = 0.9, ksize: int = 3) -> np.ndarray:
    """Combine the horizontal and vertical Sobel gradients with a weight.

    .. math::

        M = \\sqrt{w_x G_x^2 + (1 - w_x) G_y^2}

    ``wx=1`` gives :math:`|G_x|` alone, ``wx=0`` gives :math:`|G_y|` alone.

    Parameters
    ----------
    img : numpy.ndarray
        Input grayscale image, usually the output of :func:`enhance_contrast`.
    wx : float, default 0.9
        Weight of the horizontal gradient component.  Must be in [0, 1].
    ksize : int, default 3
        Sobel kernel size.  Values are coerced to the next odd integer.

    Returns
    -------
    numpy.ndarray
        Gradient magnitude, float64, unbounded.
    """
    ksize = int(ksize) | 1
    sx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=ksize)
    sy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=ksize)
    return np.sqrt(wx * (sx**2) + (1.0 - wx) * (sy**2))


def normalize_gradient(magnitude: np.ndarray, percentile: float = 99) -> np.ndarray:
    """Clip the gradient at a percentile of the whole image, then rescale it to 0-255.

    Clipping at a percentile rather than the maximum keeps a few very strong edges
    from squashing everything else.  The threshold applied afterwards is therefore
    relative to the image, not an absolute gradient value.

    Parameters
    ----------
    magnitude : numpy.ndarray
        Gradient magnitude, usually the output of :func:`weighted_gradient`.
    percentile : float, default 99
        Percentile mapped to 255.

    Returns
    -------
    numpy.ndarray
        Normalised 8-bit image.
    """
    v_max = np.percentile(magnitude, percentile)
    clipped = np.clip(magnitude, 0, v_max)
    return cv2.normalize(clipped, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def apply_weighted_sobel(
    gray: np.ndarray,
    wx: float = 0.9,
    ksize: int = 3,
    blur_size: int = 5,
    clahe_clip: float = 3.0,
    clahe_tile: int = 8,
) -> np.ndarray:
    """Enhance contrast, compute the weighted Sobel gradient and normalise it to 0-255.

    Runs :func:`enhance_contrast`, :func:`weighted_gradient` and
    :func:`normalize_gradient` in sequence; see them for the parameters.

    Returns
    -------
    numpy.ndarray
        Normalised 8-bit image containing the gradient magnitude.
    """
    enhanced = enhance_contrast(gray, blur_size=blur_size, clahe_clip=clahe_clip, clahe_tile=clahe_tile)
    return normalize_gradient(weighted_gradient(enhanced, wx=wx, ksize=ksize))


# ---------------------------------------------------------------------------
# Pixel detection
#
# detect_pixels() chains threshold_roi() -> clean_detection() -> mask_to_coords(),
# and clean_detection() chains close_gaps() -> keep_largest_component().
# ---------------------------------------------------------------------------


def crop_roi(img: np.ndarray, roi: tuple) -> np.ndarray:
    """Extract a rectangular region of interest from an image.

    Parameters
    ----------
    img : numpy.ndarray
        Input image from which to extract the region.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.

    Returns
    -------
    numpy.ndarray
        View of ``img`` restricted to the requested region.
    """
    x, y, w, h = roi
    return img[y : y + h, x : x + w]


def threshold_roi(sobel_full: np.ndarray, roi: tuple, threshold: float) -> np.ndarray:
    """Binary mask of the ROI pixels at or above ``threshold``.

    Returns
    -------
    numpy.ndarray
        Mask of the ROI's shape (uint8, values 0 or 255).
    """
    return (crop_roi(sobel_full, roi) >= threshold).astype(np.uint8) * 255


def close_gaps(binary: np.ndarray, closing_kernel: int = 3) -> np.ndarray:
    """Morphological closing (dilation then erosion) to fill small gaps along the stake.

    ``closing_kernel`` is the side of the square structuring element; 1 returns
    the mask unchanged.
    """
    if closing_kernel <= 1:
        return binary
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (closing_kernel, closing_kernel))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)


def keep_largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep only the largest connected component of a binary mask (uint8, 0 or 255)."""
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if num_labels < 2:  # only background
        return np.zeros_like(mask)

    # stats[0] is the background, skip it
    largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return (labels == largest).astype(np.uint8) * 255


def clean_detection(binary: np.ndarray, closing_kernel: int = 3) -> np.ndarray:
    """Clean a binary detection mask.

    Applies :func:`close_gaps`, then :func:`keep_largest_component` to remove
    isolated noise.

    Parameters
    ----------
    binary : numpy.ndarray
        Binary mask (uint8, values 0 or 255).
    closing_kernel : int, default 3
        Size of the square structuring element used for the closing.
        Set to 1 to disable the closing.

    Returns
    -------
    numpy.ndarray
        Cleaned binary mask (uint8, values 0 or 255).
    """
    return keep_largest_component(close_gaps(binary, closing_kernel))


def mask_to_coords(mask: np.ndarray, roi: tuple) -> np.ndarray:
    """Convert a ROI mask to full-image ``(x, y)`` coordinates, shape ``(n, 2)``."""
    x, y, _, _ = roi
    local_ys, local_xs = np.nonzero(mask)
    if len(local_xs) == 0:
        return np.empty((0, 2), dtype=int)
    return np.column_stack([local_xs + x, local_ys + y])


def detect_pixels(sobel_full: np.ndarray, roi: tuple, threshold: float, closing_kernel: int = 3) -> np.ndarray:
    """Detect high-gradient pixels inside a region of interest.

    Runs :func:`threshold_roi`, :func:`clean_detection` and :func:`mask_to_coords`.

    Parameters
    ----------
    sobel_full : numpy.ndarray
        Full-image Sobel magnitude image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    threshold : float
        Minimum Sobel magnitude required for a pixel to be retained.
    closing_kernel : int, default 3
        Passed to :func:`clean_detection`. Set to 1 to disable the closing.

    Returns
    -------
    numpy.ndarray
        Array of detected pixel coordinates with shape ``(n, 2)`` in global
        ``(x, y)`` image coordinates.  An empty integer array is returned when
        no pixels satisfy the threshold.
    """
    binary = threshold_roi(sobel_full, roi, threshold)
    return mask_to_coords(clean_detection(binary, closing_kernel), roi)


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def stakes_vertical_size(detected: np.ndarray) -> dict:
    """Return the vertical extent of detected stake pixels.

    Parameters
    ----------
    detected : numpy.ndarray
        Detected pixel coordinates with shape ``(n, 2)``.

    Returns
    -------
    dict
        ``{"y_min": int | None, "y_max": int | None, "height_px": int}``
        All values are ``None`` / ``0`` when no pixels are detected.
    """
    if len(detected) == 0:
        return {"y_min": None, "y_max": None, "height_px": 0}
    y_min = int(detected[:, 1].min())
    y_max = int(detected[:, 1].max())
    return {"y_min": y_min, "y_max": y_max, "height_px": y_max - y_min + 1}


# ---------------------------------------------------------------------------
# EXIF metadata
# ---------------------------------------------------------------------------


def read_image_date(image_path: str) -> datetime | None:
    """Read the EXIF ``DateTimeOriginal`` tag from a JPEG file.

    Parameters
    ----------
    image_path : str
        Path to the JPEG image.

    Returns
    -------
    datetime or None
        Capture datetime, or ``None`` if the tag cannot be read.
    """
    try:
        exif = piexif.load(image_path)
        raw = exif["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if raw:
            return datetime.strptime(raw.decode(), "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"EXIF read failed for {image_path}: {e}")
    return None


# ---------------------------------------------------------------------------
# Full-image detection pipeline
# ---------------------------------------------------------------------------


def detect_stakes(image_path: str, roi: tuple, best: dict) -> np.ndarray:
    """Detect stake pixels in a single image using pre-optimised parameters.

    Parameters
    ----------
    image_path : str
        Path to the input JPEG image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    best : dict
        Optimised parameter dictionary with keys ``wx``, ``threshold``,
        ``ksize``, ``clahe_clip``, and ``clahe_tile``.  Optional key
        ``closing_kernel`` (default 3) is passed to :func:`detect_pixels`.

    Returns
    -------
    numpy.ndarray
        Detected pixel coordinates with shape ``(n, 2)``.
    """
    gray = load_gray(image_path)
    sobel = apply_weighted_sobel(
        gray,
        wx=best["wx"],
        ksize=best["ksize"],
        clahe_clip=best["clahe_clip"],
        clahe_tile=best["clahe_tile"],
    )
    return detect_pixels(sobel, roi, best["threshold"], best.get("closing_kernel", 3))


# ---------------------------------------------------------------------------
# Parameter optimisation
# ---------------------------------------------------------------------------


def pixel_iou(detected: np.ndarray, ground_truth: np.ndarray) -> float:
    """Compute the intersection-over-union of detected and reference pixels.

    Parameters
    ----------
    detected : numpy.ndarray
        Detected pixel coordinates with shape ``(n, 2)``.
    ground_truth : numpy.ndarray
        Reference pixel coordinates with shape ``(m, 2)``.

    Returns
    -------
    float
        IoU score in the range ``[0, 1]``.
    """
    if len(detected) == 0:
        return 0.0
    det_set = set(map(tuple, detected))
    gt_set = set(map(tuple, ground_truth))
    inter = len(det_set & gt_set)
    union = len(det_set | gt_set)
    return inter / union if union > 0 else 0.0


def objective(params: tuple, gray: np.ndarray, roi: tuple, gt: np.ndarray) -> float:
    """Return the negative IoU for use by ``differential_evolution``.

    Parameters
    ----------
    params : tuple
        Candidate parameter vector ``(wx, threshold, ksize, clahe_clip, clahe_tile)``.
    gray : numpy.ndarray
        Input grayscale image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    gt : numpy.ndarray
        Ground-truth pixel coordinates.

    Returns
    -------
    float
        Negative IoU score (to be minimised).
    """
    wx, threshold, ksize_f, clahe_clip, clahe_tile_f = params
    wx = min(1, abs(wx))
    ksize = max(1, int(ksize_f)) | 1
    clahe_tile = max(2, int(clahe_tile_f))
    sobel = apply_weighted_sobel(gray, wx=wx, ksize=ksize, clahe_clip=clahe_clip, clahe_tile=clahe_tile)
    detected = detect_pixels(sobel, roi, threshold)
    return -pixel_iou(detected, gt)


def optimize_params(gray: np.ndarray, roi: tuple, gt: np.ndarray) -> dict:
    """Optimise Sobel and CLAHE parameters against labelled ground-truth pixels.

    Uses differential evolution (scipy) to search the parameter space defined
    by the bounds below.

    Parameters
    ----------
    gray : numpy.ndarray
        Input grayscale image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    gt : numpy.ndarray
        Ground-truth pixel coordinates used to score detections.

    Returns
    -------
    dict
        Best-found parameters: ``wx``, ``threshold``, ``ksize``,
        ``clahe_clip``, ``clahe_tile``, and the corresponding ``iou`` score.
    """
    bounds = [
        (0, 1),  # wx
        (1, 254),  # threshold
        (1, 7),  # ksize
        (0.5, 4.0),  # clahe_clip
        (8, 8),  # clahe_tile (fixed at 8 for speed)
    ]
    result = differential_evolution(
        objective,
        bounds,
        args=(gray, roi, gt),
        maxiter=100,
        tol=1e-4,
        seed=42,
        disp=True,
        workers=-1,
    )
    wx, threshold, ksize_f, clahe_clip, clahe_tile_f = result.x
    wx = min(1, abs(wx))
    ksize = max(1, int(ksize_f)) | 1
    clahe_tile = max(2, int(clahe_tile_f))
    return {
        "wx": wx,
        "threshold": threshold,
        "ksize": ksize,
        "clahe_clip": clahe_clip,
        "clahe_tile": clahe_tile,
        "iou": -result.fun,
    }
