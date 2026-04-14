import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution
from pathlib import Path
from datetime import datetime
import piexif
import pandas as pd


def load_gray(image_path: str) -> np.ndarray:
    """
    Load an image from disk and convert it to grayscale.

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


def apply_sobel(gray: np.ndarray, ksize: int = 3, clahe_clip: float = 2.0, clahe_tile: int = 8) -> np.ndarray:
    """
    Enhance local contrast and compute the Sobel gradient magnitude.

    Parameters
    ----------
    gray : numpy.ndarray
        Input grayscale image.
    ksize : int, default=3
        Sobel kernel size. The value is coerced to the next odd integer.
    clahe_clip : float, default=2.0
        Clip limit used by CLAHE.
    clahe_tile : int, default=8
        Tile grid size used by CLAHE. Values below 2 are not prevented here;
        callers are expected to provide a valid grid size.

    Returns
    -------
    numpy.ndarray
        Normalized 8-bit image containing the gradient magnitude.
    """
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))
    gray = clahe.apply(gray)
    ksize = int(ksize) | 1
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
    mag = np.sqrt(sx**2 + sy**2)
    return cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def crop_roi(img: np.ndarray, roi: tuple) -> np.ndarray:
    """
    Extract a rectangular region of interest from an image.

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


def detect_pixels(sobel_full: np.ndarray, roi: tuple, threshold: float) -> np.ndarray:
    """
    Detect high-gradient pixels inside a region of interest.

    Parameters
    ----------
    sobel_full : numpy.ndarray
        Full-image Sobel magnitude image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    threshold : float
        Minimum Sobel magnitude required for a pixel to be retained.

    Returns
    -------
    numpy.ndarray
        Array of detected pixel coordinates with shape ``(n, 2)`` in global
        ``(x, y)`` image coordinates. An empty integer array is returned when
        no pixels satisfy the threshold.
    """
    x, y, w, h = roi
    patch = sobel_full[y : y + h, x : x + w]
    local_ys, local_xs = np.where(patch >= threshold)
    if len(local_xs) == 0:
        return np.empty((0, 2), dtype=int)
    return np.column_stack([local_xs + x, local_ys + y])  # (x, y) global


def pixel_iou(detected: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Compute the intersection over union of detected and reference pixels.

    Parameters
    ----------
    detected : numpy.ndarray
        Detected pixel coordinates with shape ``(n, 2)``.
    ground_truth : numpy.ndarray
        Reference pixel coordinates with shape ``(m, 2)``.

    Returns
    -------
    float
        Intersection-over-union score in the range ``[0, 1]``.
    """
    if len(detected) == 0:
        return 0.0
    det_set = set(map(tuple, detected))
    gt_set = set(map(tuple, ground_truth))
    inter = len(det_set & gt_set)
    union = len(det_set | gt_set)
    return inter / union if union > 0 else 0.0


def objective(params, gray, roi, gt):
    """
    Return the negative IoU used by differential evolution.

    Parameters
    ----------
    params : sequence
        Candidate parameter vector containing threshold, Sobel kernel size,
        CLAHE clip limit, and CLAHE tile size.
    gray : numpy.ndarray
        Input grayscale image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    gt : numpy.ndarray
        Ground-truth pixel coordinates.

    Returns
    -------
    float
        Negative IoU score to minimize during optimization.
    """
    threshold, ksize_f, clahe_clip, clahe_tile_f = params
    ksize = max(1, int(ksize_f)) | 1
    clahe_tile = max(2, int(clahe_tile_f))
    sobel = apply_sobel(gray, ksize=ksize, clahe_clip=clahe_clip, clahe_tile=clahe_tile)
    detected = detect_pixels(sobel, roi, threshold)
    return -pixel_iou(detected, gt)


def optimize_params(gray: np.ndarray, roi: tuple, gt: np.ndarray) -> dict:
    """
    Optimize Sobel and CLAHE parameters against labeled pixels.

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
        Dictionary containing the best threshold, Sobel kernel size, CLAHE
        parameters, and the corresponding IoU score.
    """
    bounds = [
        (1, 254),  # threshold
        (1, 7),  # ksize
        (0.5, 4.0),  # clahe clipLimit
        (4, 16),  # clahe tileGridSize
    ]
    result = differential_evolution(
        objective,
        bounds,
        args=(gray, roi, gt),
        maxiter=100,
        tol=1e-4,
        seed=42,
        disp=True,
        workers=1,
    )
    threshold, ksize_f, clahe_clip, clahe_tile_f = result.x
    ksize = max(1, int(ksize_f)) | 1
    clahe_tile = max(2, int(clahe_tile_f))
    return {
        "threshold": threshold,
        "ksize": ksize,
        "clahe_clip": clahe_clip,
        "clahe_tile": clahe_tile,
        "iou": -result.fun,
    }


def visualize(image_path: str, detected: np.ndarray, roi: tuple):
    """
    Overlay detections on an image and generate full and zoomed views.

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
        Matplotlib figure and axes containing the full-image view and the ROI
        zoom.
    """
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Create RGBA overlay
    overlay = np.zeros((*img.shape[:2], 4), dtype=np.uint8)

    # Detected pixels → red, semi-transparent
    if len(detected) > 0:
        overlay[detected[:, 1], detected[:, 0]] = [255, 0, 0, 120]

    # Composite onto image
    alpha = overlay[:, :, 3:4] / 255.0
    rgb = overlay[:, :, :3]
    result = (img * (1 - alpha) + rgb * alpha).astype(np.uint8)

    # Draw ROI
    x, y, w, h = roi
    cv2.rectangle(result, (x, y), (x + w, y + h), (255, 255, 0), 1)

    pad = 20
    roi_zoom = result[y - pad : y + h + pad, x - pad : x + w + pad]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].imshow(result)
    axes[0].set_title("Full image (red=detected)")
    axes[1].imshow(roi_zoom)
    axes[1].set_title("ROI zoom")
    for ax in axes:
        ax.axis("off")

    plt.tight_layout()
    return fig, axes


def detect_balise(image_path: str, roi: tuple, best: dict) -> np.ndarray:
    """
    Return the negative IoU used by differential evolution.

    Parameters
    ----------
    params : sequence
        Candidate parameter vector containing threshold, Sobel kernel size,
        CLAHE clip limit, and CLAHE tile size.
    gray : numpy.ndarray
        Input grayscale image.
    roi : tuple
        Region of interest defined as ``(x, y, width, height)``.
    best : dict
        Dictionary containing optimized values for ``threshold``, ``ksize``,
        ``clahe_clip``, and ``clahe_tile``.

    Returns
    -------
    float
        Negative IoU score to minimize during optimization.
    """
    gray = load_gray(image_path)
    sobel = apply_sobel(gray, ksize=best["ksize"], clahe_clip=best["clahe_clip"], clahe_tile=best["clahe_tile"])
    detected = detect_pixels(sobel, roi, best["threshold"])
    return detected


def balise_vertical_size(detected: np.ndarray) -> dict:
    """Returns vertical extent of detected balise pixels."""
    if len(detected) == 0:
        return {"y_min": None, "y_max": None, "height_px": 0}
    y_min = int(detected[:, 1].min())
    y_max = int(detected[:, 1].max())
    return {"y_min": y_min, "y_max": y_max, "height_px": y_max - y_min + 1}


def read_image_date(image_path: str) -> datetime | None:
    """
    Reads EXIF DateTimeOriginal from image metadata.
    Returns datetime object or None if not found.
    """
    try:
        exif = piexif.load(image_path)
        raw = exif["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if raw:
            return datetime.strptime(raw.decode(), "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"EXIF read failed: {e}")
    return None


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    IMAGE_PATH = "photo_fixe_linceul/RCNX0094.JPG"
    # ── Ground truth for image RCNX0094.JPG (manually annotated pixels of the balise in the ROI) ──
    BALISE_GT = np.array(
        [
            [1550, 349],
            [1551, 349],
            [1550, 350],
            [1551, 350],
            [1550, 351],
            [1551, 351],
            [1550, 352],
            [1551, 352],
            [1550, 353],
            [1551, 353],
            [1550, 354],
            [1551, 354],
            [1549, 355],
            [1550, 355],
            [1551, 355],
            [1549, 356],
            [1550, 356],
            [1549, 357],
            [1550, 357],
            [1549, 358],
            [1550, 358],
            [1549, 359],
            [1550, 359],
            [1549, 360],
            [1550, 360],
            [1549, 361],
            [1550, 361],
            [1548, 362],
            [1549, 362],
            [1550, 362],
            [1548, 363],
            [1549, 363],
            [1550, 363],
            [1548, 364],
            [1549, 364],
            [1550, 364],
            [1548, 365],
            [1549, 365],
            [1548, 366],
            [1549, 366],
            [1548, 367],
            [1549, 367],
            [1548, 368],
            [1549, 368],
            [1548, 369],
            [1549, 369],
            [1547, 370],
            [1548, 370],
            [1549, 370],
            [1547, 371],
            [1548, 371],
            [1549, 371],
            [1547, 372],
            [1548, 372],
            [1547, 373],
            [1548, 373],
            [1547, 374],
            [1548, 374],
            [1547, 375],
            [1548, 375],
        ]
    )

    ROI = (1530, 330, 36, 80)  # x, y, w, h

    gray = load_gray(IMAGE_PATH)

    # print("Running optimization...")
    # best = optimize_params(gray, ROI, BALISE_GT)

    # from previous optimization:
    best = {"threshold": 35, "ksize": 3, "clahe_clip": 0.50, "clahe_tile": 4}

    print(
        f"\nBest params: threshold={best['threshold']:.1f}, ksize={best['ksize']}, "
        f"clahe_clip={best['clahe_clip']:.2f}, clahe_tile={best['clahe_tile']}"
    )

    sobel = apply_sobel(gray, ksize=best["ksize"], clahe_clip=best["clahe_clip"], clahe_tile=best["clahe_tile"])
    detected = detect_pixels(sobel, ROI, best["threshold"])

    print(f"\nDetected {len(detected)} pixels")
    print(f"GT has {len(BALISE_GT)} pixels")

    fig, axes = visualize(IMAGE_PATH, detected, ROI)
    plt.show()

    results = []

    input_dir = Path("photo_fixe_linceul")
    output_dir = Path("sobel_results")
    output_dir.mkdir(exist_ok=True)
    for img_path in sorted(input_dir.glob("*.JPG")):  # Process only the first 5 images
        print(f"\nProcessing {img_path.name}...")
        detected = detect_balise(img_path, ROI, best)
        size = balise_vertical_size(detected)
        creation_date = read_image_date(img_path.as_posix())
        fig, axes = visualize(img_path, detected, ROI)
        fig.savefig(output_dir / f"{img_path.stem}_detected.png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        results.append(
            {
                "image": img_path.name,
                "detected_pixels": len(detected),
                "balise_height_px": size["height_px"],
                "y_min": size["y_min"],
                "y_max": size["y_max"],
                "creation_date": creation_date,
            }
        )

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("image")
    results_df["creation_date"] = results_df["creation_date"].astype("datetime64[ns]").dt.strftime("%Y-%m-%d %H:%M:%S")
    results_df["creation_date"] = pd.to_datetime(results_df["creation_date"], errors="coerce")
    results_df.to_csv(output_dir / "detection_results.csv", index=False)

    # removing outliers, size = 0px and size > 67px (max expected size of the balise in the image)
    results_df[(results_df["balise_height_px"] > 0) & (results_df["balise_height_px"] < 67)].plot(
        x="creation_date", y="balise_height_px", figsize=(12, 6)
    )
    plt.title("Detected Balise Height Over Time")
    plt.xlabel("Image Creation Date")
    plt.ylabel("Balise Height (px)")
    plt.grid()
    plt.tight_layout()
    plt.savefig(output_dir / "balise_height_over_time.png")
    plt.show()
