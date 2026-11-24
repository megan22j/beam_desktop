"""JSON save/load helpers for complete beam designs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beam_calculations import (
    BeamInput,
    PointLoad,
    UniformLoad,
    validate_beam,
)


FORMAT_NAME = "Beam Designer"
FORMAT_VERSION = 1


def beam_to_dict(beam: BeamInput) -> dict[str, Any]:
    validate_beam(beam)
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "support": beam.support,
        "span": beam.span,
        "material": beam.material,
        "section": beam.section,
        "deflection_limit": beam.deflection_limit,
        "point_loads": [
            {"magnitude": load.magnitude, "position": load.position}
            for load in beam.point_loads
        ],
        "uniform_loads": [
            {
                "magnitude": load.magnitude,
                "start": load.start,
                "end": load.end,
            }
            for load in beam.uniform_loads
        ],
    }


def beam_from_dict(data: dict[str, Any]) -> BeamInput:
    if not isinstance(data, dict):
        raise ValueError("The selected file is not a beam-design JSON object.")
    if data.get("format") != FORMAT_NAME:
        raise ValueError("The selected file is not a Beam Designer file.")
    if data.get("version") != FORMAT_VERSION:
        raise ValueError("This Beam Designer file format version is not supported.")

    try:
        support = data["support"]
        span = float(data["span"])
        material = data["material"]
        section = data["section"]
        deflection_limit = int(data["deflection_limit"])
        point_data = data["point_loads"]
        uniform_data = data["uniform_loads"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The beam file is missing valid required values.") from error

    if not isinstance(point_data, list) or not isinstance(uniform_data, list):
        raise ValueError("The beam file contains invalid load lists.")

    try:
        point_loads = tuple(
            PointLoad(float(load["magnitude"]), float(load["position"]))
            for load in point_data
        )
        uniform_loads = tuple(
            UniformLoad(
                float(load["magnitude"]),
                float(load["start"]),
                float(load["end"]),
            )
            for load in uniform_data
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The beam file contains invalid load values.") from error

    beam = BeamInput(
        span=span,
        support=support,
        point_loads=point_loads,
        uniform_loads=uniform_loads,
        material=material,
        section=section,
        deflection_limit=deflection_limit,
    )
    validate_beam(beam)
    return beam


def save_beam(path: str | Path, beam: BeamInput) -> None:
    destination = Path(path)
    destination.write_text(
        json.dumps(beam_to_dict(beam), indent=2),
        encoding="utf-8",
    )


def open_beam(path: str | Path) -> BeamInput:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("The selected file is not valid JSON.") from error
    except OSError as error:
        raise ValueError(f"Could not read the selected file: {error}") from error
    return beam_from_dict(data)
