import pandas as pd
import pytest

from staketracker.io import load_data, save_results


def test_save_and_load_roundtrip(tmp_path):
    df = pd.DataFrame(
        {
            "image": ["a.JPG", "b.JPG"],
            "balise_height_px": [40, 42],
            "balise_height_m": [0.225988, 0.237288],
            "creation_date": pd.to_datetime(["2024-08-01 10:00", "2024-08-01 11:00"]),
        }
    )
    path = tmp_path / "results.csv"

    save_results(df, path, provenance={"roi": "(1, 2, 3, 4)"})

    lines = path.read_text().splitlines()
    assert lines[0].startswith("# staketracker_version: ")
    assert lines[1] == "# roi: (1, 2, 3, 4)"

    loaded = load_data([path])
    assert list(loaded["balise_height_m"]) == [0.23, 0.24]
    assert pd.api.types.is_datetime64_any_dtype(loaded["creation_date"])
    assert list(loaded["image"]) == ["a.JPG", "b.JPG"]


def test_load_data_concatenates_files(tmp_path):
    for name in ["one.csv", "two.csv"]:
        pd.DataFrame({"creation_date": ["2024-08-01 10:00"], "balise_height_px": [40]}).to_csv(
            tmp_path / name, index=False
        )
    loaded = load_data([tmp_path / "one.csv", tmp_path / "two.csv"])
    assert len(loaded) == 2


def test_load_data_requires_files():
    with pytest.raises(ValueError):
        load_data([])
