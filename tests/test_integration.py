"""End-to-end tests on the real images in ``tests/data`` (see ``tests/data/README.md``)."""

import subprocess
import sys
from pathlib import Path

import matplotlib
import pandas as pd
import pytest
from conftest import CASES, DATA_DIR, DETECTION_PARAMS

from staketracker import detect_stakes, read_image_date, stakes_vertical_size, visualize

pytestmark = pytest.mark.integration

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
PERIODS = sorted({c["period"] for c in CASES})


def _none_if_na(value):
    return None if pd.isna(value) else int(value)


def test_detect_stakes_on_real_image(case):
    detected = detect_stakes(str(case["path"]), case["roi"], case["params"])
    size = stakes_vertical_size(detected)
    assert size["height_px"] == case["height_px"], case["note"]
    assert size["y_min"] == _none_if_na(case["y_min"])
    assert size["y_max"] == _none_if_na(case["y_max"])


def test_read_image_date_on_real_image(case):
    assert read_image_date(str(case["path"])) == pd.Timestamp(case["creation_date"])


def test_visualize_on_real_image(case):
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    detected = detect_stakes(str(case["path"]), case["roi"], case["params"])
    fig, axes = visualize(str(case["path"]), detected, case["roi"])
    assert f"{case['height_px']}px" in axes[0].get_title()
    plt.close(fig)


def _run(script, *args):
    command = [sys.executable, str(SCRIPTS_DIR / script), *map(str, args)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result


@pytest.mark.parametrize("period", PERIODS)
def test_detect_then_analyze_scripts(period, tmp_path):
    cases = [c for c in CASES if c["period"] == period]
    first = cases[0]
    detection_dir = tmp_path / "detection"

    _run(
        "detect_stakes.py",
        "--input-dir", DATA_DIR / period,
        "--roi", *first["roi"],
        "--threshold", first["threshold"],
        "--wx", DETECTION_PARAMS["wx"],
        "--ksize", DETECTION_PARAMS["ksize"],
        "--clahe-clip", DETECTION_PARAMS["clahe_clip"],
        "--clahe-tile", DETECTION_PARAMS["clahe_tile"],
        "--workers", 1,
        "--output", detection_dir,
        "--save-annotated",
    )  # fmt: skip

    csv = detection_dir / "detection_results.csv"
    results = pd.read_csv(csv, comment="#").set_index("image")
    for case in cases:
        assert results.loc[case["image"], "balise_height_px"] == case["height_px"]
        assert (detection_dir / "annotated" / f"{case['image'][:-4]}_detected.png").exists()

    analysis_dir = tmp_path / "analysis"
    _run("analyze_results.py", "--input", csv, "--output", analysis_dir, "--px-per-metre", 177)

    for name in [
        "filtered_results.csv",
        "results_with_snow_level.csv",
        "balise_height_vs_time.png",
        "snow_level_vs_time.png",
    ]:
        assert (analysis_dir / name).exists(), name

    snow = pd.read_csv(analysis_dir / "results_with_snow_level.csv", comment="#")
    assert (snow["snow_level_m"] >= 0).all()


def test_step_by_step_notebook_runs():
    """The notebook redoes the pipeline by hand and asserts it matches detect_stakes()."""
    nbclient = pytest.importorskip("nbclient", reason="needs the jupyter extra")
    import nbformat

    notebook_path = Path(__file__).parents[1] / "notebooks" / "pipeline_step_by_step.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    client = nbclient.NotebookClient(notebook, timeout=120, resources={"metadata": {"path": notebook_path.parent}})
    client.execute()
