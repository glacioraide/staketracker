#!/usr/bin/env python3
"""Batch stake detection: process every image in a directory and record stakes heights.

For each JPEG in the input directory the Sobel-based detection pipeline is
applied to a user-defined region of interest (ROI).  Results are accumulated
and written as ``detection_results.csv`` in a date-stamped output directory.

Usage example::

    python scripts/detect_stakes.py \\
        --input-dir /path/to/images/ \\
        --roi 1835 330 20 80 \\
        --output analysis/detection

Detection parameters (``--wx``, ``--threshold``, etc.) default to the
best-known values tuned on the Linceul fixed camera.  Override them when using
a different camera setup or after running parameter optimisation.

Optionally pass ``--save-annotated`` to write one PNG per image with the
detected pixels overlaid (useful for quality control).
"""

import argparse
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from staketracker.detection import (
    balise_vertical_size,
    detect_balise,
    read_image_date,
    visualize,
)
from staketracker.io import save_results


def main() -> None:
    """Batch-detect the stake in every image and write a detection CSV."""
    parser = argparse.ArgumentParser(
        description="Detect the stake in JPEG images and record balise heights in pixels",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        required=True,
        metavar="DIR",
        help="Directory containing JPEG images to process",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="detection",
        metavar="DIR",
        help="Base name for the output directory (run date is appended automatically)",
    )
    parser.add_argument(
        "--roi",
        nargs=4,
        type=int,
        required=True,
        metavar=("X", "Y", "W", "H"),
        help="Region of interest: X Y W H (top-left corner, then width and height in pixels)",
    )
    parser.add_argument(
        "--glob",
        default="*.JPG",
        metavar="PATTERN",
        help="Glob pattern used to select images inside --input-dir",
    )
    parser.add_argument(
        "--wx",
        type=float,
        default=0.9,
        help="Weight of the horizontal Sobel gradient component (0–1)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="Sobel magnitude threshold for pixel detection",
    )
    parser.add_argument(
        "--ksize",
        type=int,
        default=1,
        help="Sobel kernel size (rounded to the next odd integer internally)",
    )
    parser.add_argument(
        "--clahe-clip",
        type=float,
        default=1.0,
        dest="clahe_clip",
        help="CLAHE clip limit",
    )
    parser.add_argument(
        "--clahe-tile",
        type=int,
        default=2,
        dest="clahe_tile",
        help="CLAHE tile grid size",
    )
    parser.add_argument(
        "--save-annotated",
        action="store_true",
        help="Save a PNG with detections overlaid for every processed image (slow)",
    )
    args = parser.parse_args()

    run_date = datetime.now().strftime("%Y-%m-%d")
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    output_dir = Path(f"{args.output}_{run_date}")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    input_dir = Path(args.input_dir)
    images = sorted(input_dir.glob(args.glob))
    if not images:
        raise SystemExit(f"No images matching '{args.glob}' found in {input_dir}")

    roi: tuple[int, int, int, int] = tuple(args.roi)  # type: ignore[assignment]
    detection_params = {
        "wx": args.wx,
        "threshold": args.threshold,
        "ksize": args.ksize,
        "clahe_clip": args.clahe_clip,
        "clahe_tile": args.clahe_tile,
    }

    print("=" * 70)
    print("DETECTION PARAMETERS")
    print("=" * 70)
    print(f"  ROI              : x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}")
    for key, value in detection_params.items():
        print(f"  {key:<17}: {value}")
    print(f"  Images found     : {len(images)}")
    print()

    if args.save_annotated:
        annotated_dir = output_dir / "annotated"
        annotated_dir.mkdir(exist_ok=True)
        matplotlib.use("Agg")  # non-interactive backend for batch saving

    print("=" * 70)
    print("PROCESSING IMAGES")
    print("=" * 70)

    rows = []
    for img_path in images:
        detected = detect_balise(img_path.as_posix(), roi, detection_params)
        size = balise_vertical_size(detected)
        creation_date = read_image_date(img_path.as_posix())

        if args.save_annotated:
            fig, _ = visualize(img_path.as_posix(), detected, roi)
            fig.savefig(
                annotated_dir / f"{img_path.stem}_detected.png",
                dpi=100,
                bbox_inches="tight",
            )
            plt.close(fig)

        rows.append(
            {
                "image": img_path.name,
                "detected_pixels": len(detected),
                "balise_height_px": size["height_px"],
                "y_min": size["y_min"],
                "y_max": size["y_max"],
                "creation_date": creation_date,
            }
        )
        print(f"  {img_path.name}: {size['height_px']} px  ({len(detected)} detected pixels)")

    print()
    print("=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    results_df = pd.DataFrame(rows).sort_values("image").reset_index(drop=True)
    results_df["creation_date"] = pd.to_datetime(results_df["creation_date"], errors="coerce")

    provenance = {
        "generated_at": generated_at,
        "input_dir": str(input_dir.resolve()),
        "roi": str(roi),
        "detection_params": str(detection_params),
    }
    save_results(results_df, output_dir / "detection_results.csv", provenance=provenance)

    print()
    print("=" * 70)
    print("✓ DETECTION COMPLETE")
    print("=" * 70)
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
