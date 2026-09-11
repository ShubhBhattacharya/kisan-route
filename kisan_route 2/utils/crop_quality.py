"""Placeholder computer-vision crop grading.

Swap `analyze_crop_image` for a real model call (e.g. a CNN classifier
served over an API) later. It currently derives a deterministic-ish grade
from the filename so the same demo photo always grades the same way in a
live demo, which is more convincing than pure randomness.
"""
import random

GRADES = ["Excellent", "Good", "Average", "A", "B", "C"]


def analyze_crop_image(filename: str) -> dict:
    seed = sum(ord(c) for c in filename) if filename else 0
    rng = random.Random(seed)
    grade = rng.choice(GRADES)
    confidence = rng.randint(72, 98)
    return {"grade": grade, "confidence": confidence}
