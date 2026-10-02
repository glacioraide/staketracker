# Choose the ROI and threshold

Each camera setup needs its own region of interest (ROI) and threshold. If the camera moves,
for example when it is serviced, start again for the new period.

## Find the ROI

1. Pick the photo where the stake is the longest, usually at the end of the melt season.
2. Open it in an image viewer that shows pixel coordinates (Preview, GIMP,
   [pixspy.com](https://pixspy.com/)). Coordinates start at the top-left corner.
3. Note the top-left corner `x y` of a rectangle around the stake, then its width and height.
   Leave a margin of 10 to 20 pixels: the stake leans and the camera shifts a little.
4. Pass the four numbers to `--roi x y width height`.

Keep the ROI narrow. Rocks or snow edges inside it can be detected as stake.

## Tune the threshold

Run the detection on a dozen photos with different conditions (sun, shade, snow, fog), and save the
annotated images:

```bash
python scripts/detect_stakes.py \
    --input-dir sample/ \
    --roi 1820 310 50 140 \
    --threshold 140 \
    --output tuning \
    --save-annotated \
    --overwrite
```

Look at `tuning/annotated/`, then adjust:

| You see | Do |
| --- | --- |
| The stake is cut in pieces, or too short | Lower `--threshold` |
| Pixels outside the stake are red | Raise `--threshold`, or narrow the ROI |
| Nothing detected on a clear photo | Lower `--threshold` a lot, check the ROI |

Values between 60 and 200 are common. On fog or snow-covered photos, finding nothing is correct.

The other parameters (`--wx`, `--ksize`, `--clahe-clip`, `--clahe-tile`) rarely need changing.
[Detection step by step](../notebooks/pipeline_step_by_step.md) shows what each one does.
