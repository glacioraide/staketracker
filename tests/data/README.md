# Test images

Six photos from the fixed camera on the Linceul glacier, two per acquisition period.
They come unmodified from the EDYTEM dataset (`Traitement_Images/linceul_*`), EXIF included.

`cases.csv` lists, for each image, the ROI and threshold used for that period (same values as
`workflow.sh`) and the expected detection result. The integration tests and
`notebooks/pipeline_step_by_step.ipynb` read this file.

| Period | Image | Content |
|---|---|---|
| 2024-07-17 → 2024-11-10 | RCNX0452 | clear stake, 62 px |
| 2024-07-17 → 2024-11-10 | RCNX0579 | fog, no detection |
| 2024-11-11 → 2025-03-31 | RCNX1313 | clear stake, 42 px |
| 2024-11-11 → 2025-03-31 | RCNX0373 | fog, no detection |
| 2025-04-01 → 2025-10-10 | RCNX2325 | clear stake, 77 px |
| 2025-04-01 → 2025-10-10 | RCNX1995 | clear stake, 54 px |

If a code change moves these values on purpose, check the new result visually
(`scripts/detect_stakes.py --save-annotated`) before updating `cases.csv`.
