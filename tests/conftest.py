from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parent / "data"

DETECTION_PARAMS = {"wx": 0.9, "ksize": 1, "clahe_clip": 1.0, "clahe_tile": 2}


def load_cases() -> list[dict]:
    """Rows of ``tests/data/cases.csv`` with the image path, ROI and detection parameters resolved."""
    cases = pd.read_csv(DATA_DIR / "cases.csv", comment="#", dtype={"y_min": "Int64", "y_max": "Int64"})
    rows = []
    for row in cases.to_dict("records"):
        row["path"] = DATA_DIR / row["period"] / row["image"]
        row["roi"] = (row["roi_x"], row["roi_y"], row["roi_w"], row["roi_h"])
        row["params"] = {**DETECTION_PARAMS, "threshold": row["threshold"]}
        rows.append(row)
    return rows


CASES = load_cases()


@pytest.fixture(params=CASES, ids=[f"{c['period'][8:16]}-{c['image'][:-4]}" for c in CASES])
def case(request):
    return request.param
