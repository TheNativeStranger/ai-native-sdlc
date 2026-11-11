#!/usr/bin/env python3
"""Deterministic detection: compares the latest value of one metric with its rolling baseline.

No model is involved. Reads a JSON list of numbers (oldest first, latest last) and the tiers in
bands.json, and prints which tier, if any, the latest value breaches.

Usage: detect.py <bands.json> <series.json>
Exit code: 0 inside the bands, 10 log, 20 diagnose, 30 propose.
"""
import json
import statistics
import sys

CODES = {"none": 0, "log": 10, "diagnose": 20, "propose": 30}


def drift(z):
    """Run rules that catch slow drift before a single point breaches a band."""
    last = z[-8:]
    if len(last) == 8 and (all(v > 0 for v in last) or all(v < 0 for v in last)):
        return "eight points in a row on one side of the baseline"
    last = z[-5:]
    if len(last) == 5 and max(sum(v > 1 for v in last), sum(v < -1 for v in last)) >= 4:
        return "four of the last five points beyond one sigma on one side"
    last = z[-3:]
    if len(last) == 3 and max(sum(v > 2 for v in last), sum(v < -2 for v in last)) >= 2:
        return "two of the last three points beyond two sigma on one side"
    return None


def evaluate(bands, series):
    window = int(bands.get("window", 30))
    if len(series) < 9:
        return {"tier": "none", "reason": "not enough history for a baseline"}
    baseline, latest = series[-(window + 1):-1], series[-1]
    mean, sigma = statistics.fmean(baseline), statistics.pstdev(baseline)
    if sigma == 0:
        return {"tier": "none" if latest == mean else "diagnose", "mean": mean, "sigma": 0.0, "latest": latest,
                "reason": "flat baseline" if latest == mean else "the value moved off a flat baseline"}
    z = [(value - mean) / sigma for value in baseline[-7:]] + [(latest - mean) / sigma]
    score = abs(z[-1])
    tier = "propose" if score >= 3 else "diagnose" if score >= 2 else "log" if score >= 1 else "none"
    reason = f"latest value is {score:.1f} sigma from the rolling mean"
    rule = drift(z) if bands.get("rules", "western_electric") == "western_electric" else None
    if rule and CODES[tier] < CODES["diagnose"]:
        tier, reason = "diagnose", rule
    return {"tier": tier, "mean": round(mean, 4), "sigma": round(sigma, 4), "latest": latest, "reason": reason}


if __name__ == "__main__":
    bands = json.load(open(sys.argv[1], encoding="utf-8"))
    series = json.load(open(sys.argv[2], encoding="utf-8"))
    result = evaluate(bands, series)
    result["metric"] = bands.get("metric")
    result["action"] = bands.get("tiers", {}).get(result["tier"], {})
    print(json.dumps(result))
    sys.exit(CODES[result["tier"]])
