from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import write_report
from .loudness import analyze_loudness
from .spectrum import analyze_spectrum


def compare_reference(
    *,
    candidate: str | Path,
    reference: str | Path,
    metrics: str = "loudness,spectrum,stereo",
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    requested = {item.strip() for item in metrics.split(",") if item.strip()}
    delta: dict[str, float] = {}
    recommendations: list[dict[str, str]] = []

    if "loudness" in requested:
        candidate_loudness = analyze_loudness(candidate)
        reference_loudness = analyze_loudness(reference)
        for key in ("integrated_lufs", "true_peak_dbtp", "rms_dbfs", "crest_db"):
            delta[key] = round(candidate_loudness[key] - reference_loudness[key], 3)
        if delta["true_peak_dbtp"] > -0.5:
            recommendations.append(
                {
                    "scope": "master",
                    "code": "limiter_margin",
                    "message": "True peak is close to ceiling; avoid further global gain",
                }
            )

    if "spectrum" in requested or "stereo" in requested:
        candidate_spectrum = analyze_spectrum(candidate)
        reference_spectrum = analyze_spectrum(reference)
        if "spectrum" in requested:
            for key, value in candidate_spectrum["bands"].items():
                delta[key] = round(value - reference_spectrum["bands"][key], 3)
            if delta.get("air_10000_18000_hz", 0.0) < -3.0:
                recommendations.append(
                    {
                        "scope": "mix",
                        "code": "air_low",
                        "message": "Consider brightening hats/synth air before adding master shelf",
                    }
                )
            if delta.get("presence_2000_6000_hz", 0.0) > 3.0:
                recommendations.append(
                    {
                        "scope": "mix",
                        "code": "presence_hot",
                        "message": "Check vocal/lead balance before using master EQ cuts",
                    }
                )
        if "stereo" in requested:
            for key in ("correlation_avg", "side_energy_ratio"):
                delta[key] = round(
                    candidate_spectrum["stereo"][key] - reference_spectrum["stereo"][key],
                    3,
                )

    result = {
        "candidate": str(Path(candidate).expanduser()),
        "reference": str(Path(reference).expanduser()),
        "metrics": sorted(requested),
        "delta": delta,
        "recommendations": recommendations,
    }
    write_report(report_out, result)
    return result
