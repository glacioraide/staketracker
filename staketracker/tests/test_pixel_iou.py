import numpy as np
from staketracker.detection import pixel_iou


def test_pixel_iou_basic():
    # Simple perfect overlap
    detected = np.array([[0, 0], [1, 1], [2, 2]])
    ground_truth = np.array([[0, 0], [1, 1], [2, 2]])
    assert pixel_iou(detected, ground_truth) == 1.0


def test_pixel_iou_partial():
    detected = np.array([[0, 0], [1, 1], [2, 2]])
    ground_truth = np.array([[1, 1], [2, 2], [3, 3]])
    # Intersection has two points, union has four
    assert pixel_iou(detected, ground_truth) == 0.5


def test_pixel_iou_empty_detected():
    detected = np.empty((0, 2), dtype=int)
    ground_truth = np.array([[0, 0]])
    assert pixel_iou(detected, ground_truth) == 0.0
