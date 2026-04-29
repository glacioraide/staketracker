import numpy as np
import cv2
import matplotlib.pyplot as plt
import pandas as pd
from .detection import stakes_vertical_size

# ---------------------------------------------------------------------------
# Plotting Functions
# ---------------------------------------------------------------------------


def plot_height_vs_time(raw_results, filtered_results, output_file=None):
    fig, ax = plt.subplots(figsize=(14, 6))
    raw_results.plot(
        x="creation_date", y="balise_height_px", ax=ax, alpha=0.35, linewidth=1, label="Hauteur détectée (brute)"
    )
    filtered_results.plot.scatter(
        x="creation_date",
        y="balise_height_px_moving_average",
        ax=ax,
        label="Hauteur filtrée (moyenne mobile 24h)",
        color="orange",
        marker="_",
        s=100,
    )
    ax.invert_yaxis()
    ax.set_title("Hauteur de la balise au fil du temps")
    ax.set_xlabel("Date")
    ax.set_ylabel("Hauteur de la balise (px)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    plt.tight_layout()
    if output_file:
        print(f"Saving plot to {output_file}...")
        plt.savefig(output_file, dpi=300)
        print(f"✓ Saved plot to {output_file}")
    else:
        plt.show()


def plot_snow_level(results_m, output_file=None, **kwargs):
    fig, ax = plt.subplots(figsize=(16, 6))
    kwargs.setdefault("label", "Niveau de neige estimé")
    kwargs.setdefault("color", "steelblue")
    kwargs.setdefault("linewidth", 2.5)
    results_m.plot.scatter(x="creation_date", y="snow_level_m", ax=ax, **kwargs)
    ax.set_title("Niveau de neige estimé au fil du temps")
    ax.set_xlabel("Date")
    ax.set_ylabel("Niveau de neige (m)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    plt.tight_layout()
    if output_file:
        print(f"Saving plot to {output_file}...")
        plt.savefig(output_file, dpi=300)
        print(f"✓ Saved plot to {output_file}")
    else:
        plt.show()


def plot_snow_level_with_meteo(results_m, meteo_file, output_file=None):
    try:
        meteo = pd.read_csv(meteo_file)
        meteo["date"] = (
            pd.to_datetime(meteo["date"], errors="coerce", utc=True).dt.tz_convert("Europe/Paris").dt.tz_localize(None)
        )
    except FileNotFoundError:
        print(f"Warning: Meteorological file not found: {meteo_file}")
        return
    fig, ax = plt.subplots(figsize=(16, 6))
    results_m.plot.scatter(
        x="creation_date",
        y="snow_level_m",
        ax=ax,
        label="Niveau de neige (balise)",
        color="steelblue",
        marker=".",
        s=30,
    )
    date_min = results_m["creation_date"].min()
    date_max = results_m["creation_date"].max()
    ax2 = ax.twinx()
    if "precipitation_sum" in meteo.columns:
        daily = meteo.set_index("date")["precipitation_sum"].loc[date_min:date_max].resample("1D").sum()
        ax2.bar(daily.index, daily.values, width=1, color="red", alpha=0.3, label="Précipitations totales (mm/jour)")
    ax.set_title("Niveau de neige vs Précipitations")
    ax.set_xlabel("Date")
    ax.set_ylabel("Niveau de neige (m)", color="steelblue")
    ax2.set_ylabel("Précipitations (mm)", color="red")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")
    plt.tight_layout()
    if output_file:
        print(f"Saving plot to {output_file}...")
        plt.savefig(output_file, dpi=300)
        print(f"✓ Saved plot to {output_file}")
    else:
        plt.show()


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

    stakes_height = stakes_vertical_size(detected)["height_px"]

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
    axes[0].set_title(f"Full image (red=detected) - Stakes height: {stakes_height}px")
    axes[1].imshow(roi_zoom)
    axes[1].set_title("ROI zoom")
    for ax in axes:
        ax.axis("off")

    plt.tight_layout()
    return fig, axes
