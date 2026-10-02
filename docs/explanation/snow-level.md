# From pixels to snow level

The camera does not see the snow depth. It sees how much of the stake sticks out. When snow
falls, the visible part gets shorter; when snow melts, it gets longer. staketracker measures
that visible height in each photo, then derives the snow level from it.

## Measuring the height

The stake is a thin, dark, vertical line on bright snow, so it shows up as a strong edge.
The detection keeps the strongest edges inside the ROI, removes isolated pixels, and measures
the vertical extent of what is left. [Detection step by step](../notebooks/pipeline_step_by_step.md)
shows each stage on real photos.

Some photos give a wrong height: fog, snow on the lens, a person next to the stake, low sun.
A single photo cannot tell, but the series can, since snow does not change by tens of
centimetres between two photos.

## Cleaning the series

`analyze_results.py` removes, in order:

1. photos without a capture date,
2. heights below 10 or above 100 pixels, which cannot be the stake,
3. heights more than 10 pixels away from the median of their neighbours (sudden jumps).

It then averages the remaining heights over 24 hours.

## Snow level

The heights are converted to metres with the pixels-per-metre factor. The snow level is then:

```text
snow_level = highest visible height of the series - visible height
```

So the snow level is relative: 0 is the lowest snow surface seen during the series, usually at
the end of the melt season. It is not the depth above the ice, unless the stake was seen bare.

## Limits

- The camera must not move within a period. If it does, the ROI no longer matches.
- Pixels per metre is a single value, measured at the distance of the stake.
- The stake must stay upright. A leaning stake looks shorter.
