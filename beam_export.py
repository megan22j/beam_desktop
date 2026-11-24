"""CSV export helpers for calculated beam results."""

from __future__ import annotations

import csv
from pathlib import Path

from beam_calculations import Analysis


def analysis_to_csv(path: str | Path, analysis: Analysis) -> None:
    destination = Path(path)
    with destination.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(("x_ft", "V_kips", "M_kip_ft", "deflection_in"))
        for sample in analysis.samples:
            writer.writerow(
                (
                    f"{sample.x:.6f}",
                    f"{sample.shear:.6f}",
                    f"{sample.moment:.6f}",
                    f"{sample.deflection:.6f}",
                )
            )
