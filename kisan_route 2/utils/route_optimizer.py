"""Placeholder route optimizer.

Later this can call a real routing engine (OSRM, Google Directions, a
custom VRP solver, etc.). It should keep returning a dict with
`waypoints`, `distance_km`, and `eta_minutes` so `driver` templates don't
need to change.
"""


def optimize_route(pickup: str, drop: str) -> dict:
    waypoints = [pickup, f"{pickup} Highway Junction", f"{drop} Bypass Road", drop]
    distance_km = round((len(pickup) + len(drop)) * 1.6, 1)
    eta_minutes = int(distance_km * 2.1) + 10
    return {"waypoints": waypoints, "distance_km": distance_km, "eta_minutes": eta_minutes}
