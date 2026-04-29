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

import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution
from datetime import datetime
import piexif


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
# ---------------------------------------------------------------------------


def apply_weighted_sobel(
    gray: np.ndarray,
    wx: float = 0.9,
    ksize: int = 3,
    blur_size: int = 5,
    clahe_clip: float = 3.0,
    clahe_tile: int = 8,
) -> np.ndarray:
    """Apply CLAHE contrast enhancement and compute a weighted Sobel gradient.

    The horizontal and vertical gradient components are combined as:

    .. math::

        M = \\sqrt{w_x G_x^2 + (1 - w_x) G_y^2}

    Parameters
    ----------
    gray : numpy.ndarray
        Input grayscale image.
    wx : float, default 0.9
        Weight of the horizontal gradient component.  Must be in [0, 1].
    ksize : int, default 3
        Sobel kernel size.  Values are coerced to the next odd integer.
    blur_size : int, default 5
        Gaussian blur kernel size applied before CLAHE.
    clahe_clip : float, default 3.0
        Clip limit used by CLAHE.
    clahe_tile : int, default 8
        Tile grid size used by CLAHE.  Values below 2 are rejected by OpenCV.

    Returns
    -------
    numpy.ndarray
        Normalised 8-bit image containing the gradient magnitude.
    """
    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))
    enhanced = clahe.apply(blurred)

    ksize = int(ksize) | 1
    sx = cv2.Sobel(enhanced, cv2.CV_64F, 1, 0, ksize=ksize)
    sy = cv2.Sobel(enhanced, cv2.CV_64F, 0, 1, ksize=ksize)

    wy = 1.0 - wx
    weighted_mag = np.sqrt(wx * (sx**2) + wy * (sy**2))

    # Percentile-based normalisation for robustness under varying illumination
    v_max = np.percentile(weighted_mag, 99)
    weighted_mag = np.clip(weighted_mag, 0, v_max)

    return cv2.normalize(weighted_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


# ---------------------------------------------------------------------------
# Pixel detection
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


def detect_pixels(sobel_full: np.ndarray, roi: tuple, threshold: float, opening_kernel: int = 1) -> np.ndarray:
    """Detect high-gradient pixels inside a region of interest.

    Parameters
    ----------
    sobel_full : numpy.ndarray
        Full-image Sobel magnitude image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    threshold : float
        Minimum Sobel magnitude required for a pixel to be retained.
    opening_kernel : int, default 1
        Size of the square structuring element used for morphological opening.
        Set to 1 to disable opening.

    Returns
    -------
    numpy.ndarray
        Array of detected pixel coordinates with shape ``(n, 2)`` in global
        ``(x, y)`` image coordinates.  An empty integer array is returned when
        no pixels satisfy the threshold.
    """
    x, y, w, h = roi
    patch = sobel_full[y : y + h, x : x + w]

    binary = (patch >= threshold).astype(np.uint8) * 255

    local_ys, local_xs = np.where(binary > 0)
    if len(local_xs) == 0:
        return np.empty((0, 2), dtype=int)
    return np.column_stack([local_xs + x, local_ys + y])


def apply_opening(binary: np.ndarray, kernel_size: int = 1) -> np.ndarray:
    """Apply morphological opening to remove small noise pixels.

    Parameters
    ----------
    binary : numpy.ndarray
        Binary mask (uint8, values 0 or 255).
    kernel_size : int, default 1
        Size of the square structuring element.

    Returns
    -------
    numpy.ndarray
        Opened binary mask.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)


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
        ``ksize``, ``clahe_clip``, and ``clahe_tile``.

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
    return detect_pixels(sobel, roi, best["threshold"])


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


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------


def visualize(image_path: str, detected: np.ndarray, roi: tuple):
    """Overlay detections on an image and return full and zoomed views.

    Parameters
    ----------
    image_path : str
        Path to the image to display.
    detected : numpy.ndarray
        Detected pixel coordinates with shape ``(n, 2)``.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.

    Returns
    -------
    tuple
        Matplotlib ``(figure, axes)`` with the full-image view and the ROI
        zoom.
    """
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    overlay = np.zeros((*img.shape[:2], 4), dtype=np.uint8)

    if len(detected) > 0:
        overlay[detected[:, 1], detected[:, 0]] = [255, 0, 0, 120]

    stakes_height = stakes_vertical_size(detected)["height_px"]

    alpha = overlay[:, :, 3:4] / 255.0
    rgb = overlay[:, :, :3]
    result = (img * (1 - alpha) + rgb * alpha).astype(np.uint8)

    x, y, w, h = roi
    cv2.rectangle(result, (x, y), (x + w, y + h), (255, 255, 0), 1)

    pad = 20
    roi_zoom = result[y - pad : y + h + pad, x - pad : x + w + pad]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].imshow(result)
    axes[0].set_title(f"Full image (red=detected) – stakes height: {stakes_height} px")
    axes[1].imshow(roi_zoom)
    axes[1].set_title("ROI zoom")
    for ax in axes:
        ax.axis("off")

    plt.tight_layout()
    return fig, axes
