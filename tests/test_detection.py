import numpy as np

from staketracker.detection import (
    apply_weighted_sobel,
    clean_detection,
    close_gaps,
    crop_roi,
    detect_pixels,
    enhance_contrast,
    mask_to_coords,
    normalize_gradient,
    read_image_date,
    stakes_vertical_size,
    weighted_gradient,
)


def _edges_image():
    """Grey image with a dark top-left quadrant: one vertical and one horizontal edge of equal contrast."""
    img = np.full((200, 200), 200, dtype=np.uint8)
    img[:100, :100] = 50
    return img


def test_apply_weighted_sobel_output_format():
    out = apply_weighted_sobel(_edges_image())
    assert out.dtype == np.uint8
    assert out.shape == (200, 200)


def test_apply_weighted_sobel_wx_favours_vertical_edges():
    img = _edges_image()
    vertical_edge = (slice(20, 80), slice(95, 105))
    horizontal_edge = (slice(95, 105), slice(20, 80))

    out = apply_weighted_sobel(img, wx=0.9)
    assert out[vertical_edge].max() > out[horizontal_edge].max()

    out = apply_weighted_sobel(img, wx=0.1)
    assert out[vertical_edge].max() < out[horizontal_edge].max()


def test_crop_roi():
    img = np.arange(100).reshape(10, 10)
    patch = crop_roi(img, (2, 3, 4, 5))  # x, y, w, h
    assert patch.shape == (5, 4)
    assert patch[0, 0] == img[3, 2]


def test_detect_pixels_returns_global_coordinates():
    sobel = np.zeros((100, 100), dtype=np.uint8)
    sobel[20:40, 55] = 255  # stake inside the ROI
    sobel[5, 5] = 255  # bright pixel outside the ROI
    roi = (50, 10, 10, 40)

    detected = detect_pixels(sobel, roi, threshold=100)

    assert len(detected) == 20
    assert set(detected[:, 0]) == {55}
    assert detected[:, 1].min() == 20
    assert detected[:, 1].max() == 39


def test_detect_pixels_nothing_above_threshold():
    sobel = np.full((100, 100), 50, dtype=np.uint8)
    detected = detect_pixels(sobel, (10, 10, 20, 20), threshold=100)
    assert detected.shape == (0, 2)


def test_stakes_vertical_size():
    detected = np.array([[5, 12], [5, 20], [6, 15]])
    assert stakes_vertical_size(detected) == {"y_min": 12, "y_max": 20, "height_px": 9}


def test_stakes_vertical_size_empty():
    detected = np.empty((0, 2), dtype=int)
    assert stakes_vertical_size(detected) == {"y_min": None, "y_max": None, "height_px": 0}


def test_read_image_date_without_exif(tmp_path):
    path = tmp_path / "not_an_image.jpg"
    path.write_bytes(b"not a jpeg")
    assert read_image_date(str(path)) is None


def test_clean_detection_keeps_largest_component():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2:15, 5] = 255  # stake
    mask[18, 18] = 255  # isolated noise
    cleaned = clean_detection(mask, closing_kernel=1)
    assert cleaned[18, 18] == 0
    assert (cleaned[2:15, 5] == 255).all()


def test_clean_detection_closing_fills_gap():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2:8, 5] = 255
    mask[9:15, 5] = 255  # one-pixel gap at row 8
    assert clean_detection(mask, closing_kernel=1)[8, 5] == 0
    assert clean_detection(mask, closing_kernel=3)[8, 5] == 255


def test_clean_detection_empty_mask():
    mask = np.zeros((20, 20), dtype=np.uint8)
    assert not clean_detection(mask).any()


def test_apply_weighted_sobel_chains_the_three_steps():
    img = _edges_image()
    steps = normalize_gradient(weighted_gradient(enhance_contrast(img, clahe_tile=2), wx=0.7, ksize=1))
    assert (apply_weighted_sobel(img, wx=0.7, ksize=1, clahe_tile=2) == steps).all()


def test_weighted_gradient_extreme_weights_keep_one_component():
    img = _edges_image().astype(np.float64)
    vertical_edge = (slice(20, 80), slice(95, 105))
    horizontal_edge = (slice(95, 105), slice(20, 80))
    gx_only = weighted_gradient(img, wx=1, ksize=3)
    assert gx_only[vertical_edge].max() > 0
    assert gx_only[horizontal_edge].max() == 0


def test_normalize_gradient_maps_percentile_to_255():
    magnitude = np.arange(1000, dtype=np.float64).reshape(10, 100)
    out = normalize_gradient(magnitude, percentile=50)
    assert out.dtype == np.uint8
    assert out.min() == 0
    assert (out[magnitude >= np.percentile(magnitude, 50)] == 255).all()


def test_close_gaps_kernel_one_is_identity():
    mask = np.zeros((10, 10), dtype=np.uint8)
    mask[2:4, 5] = 255
    mask[5:8, 5] = 255
    assert (close_gaps(mask, closing_kernel=1) == mask).all()


def test_mask_to_coords_offsets_by_roi():
    mask = np.zeros((5, 4), dtype=np.uint8)
    mask[1, 2] = 255
    assert mask_to_coords(mask, (10, 20, 4, 5)).tolist() == [[12, 21]]
    assert mask_to_coords(np.zeros_like(mask), (10, 20, 4, 5)).shape == (0, 2)
