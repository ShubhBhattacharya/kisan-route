"""Mock mandi (market) rate lookup.

Replace `get_mandi_rates` with a real call to a mandi price API or scraped
dataset later — keep the same return shape (list of {region, rate} dicts,
sorted best-first) so templates don't need to change.
"""
import random

REGIONS = [
    "Azadpur Mandi (Delhi)",
    "Narela Mandi (Delhi)",
    "Ghazipur Mandi (Delhi)",
    "Dadri Mandi",
    "Faridabad Mandi",
    "Ghaziabad Mandi",
    "Sonipat Mandi",
    "Meerut Mandi",
    "Palwal Mandi",
    "Rohtak Mandi",
    "Bulandshahr Mandi",
]

BASE_RATES = {
    "Wheat": 2200,
    "Rice": 2800,
    "Sugarcane": 350,
    "Mustard": 5400,
    "Potato": 1200,
    "Onion": 1800,
    "Tomato": 1500,
    "Cotton": 6200,
}


def list_crops():
    return list(BASE_RATES.keys())


def get_mandi_rates(crop: str):
    base = BASE_RATES.get(crop, 2000)
    rng = random.Random(f"{crop}-{__import__('datetime').date.today()}")
    rates = []
    for region in REGIONS:
        variation = rng.randint(-150, 220)
        rates.append({"region": region, "rate": base + variation})
    rates.sort(key=lambda r: r["rate"], reverse=True)
    return rates
