"""Pure beam-analysis functions used by the Tkinter interface."""

from __future__ import annotations

from dataclasses import dataclass
from math import copysign, isfinite, sqrt
from typing import Iterable, Literal


Support = Literal["Simply supported", "Cantilever"]
Material = Literal["Steel", "Lumber"]


@dataclass(frozen=True)
class PointLoad:
    magnitude: float
    position: float


@dataclass(frozen=True)
class UniformLoad:
    magnitude: float
    start: float
    end: float


@dataclass(frozen=True)
class Section:
    name: str
    material: Material
    E: float
    Fb: float
    Ix: float
    Sx: float
    weight: float | None = None


@dataclass(frozen=True)
class BeamInput:
    span: float = 20.0
    support: Support = "Simply supported"
    point_loads: tuple[PointLoad, ...] = ()
    uniform_loads: tuple[UniformLoad, ...] = (UniformLoad(1.0, 0.0, 20.0),)
    material: Material = "Steel"
    section: str = "W12x26"
    deflection_limit: int = 360


@dataclass(frozen=True)
class Reactions:
    left: float
    right: float
    fixed_moment: float


@dataclass(frozen=True)
class BeamSample:
    x: float
    shear: float
    moment: float
    deflection: float


@dataclass(frozen=True)
class Analysis:
    reactions: Reactions
    samples: tuple[BeamSample, ...]
    shear_curve: tuple[tuple[float, float], ...]
    max_shear: float
    max_shear_x: float
    max_moment: float
    max_moment_x: float
    max_deflection: float
    max_deflection_x: float
    bending_stress: float
    bending_allowable: float
    bending_ratio: float
    bending_pass: bool
    deflection_allowable: float
    deflection_ratio: float
    deflection_pass: bool
    recommendation: Section | None


STEEL_SECTIONS = (
    Section("W8x10", "Steel", 29000.0, 30.0, 30.8, 7.81, 10.0),
    Section("W10x12", "Steel", 29000.0, 30.0, 53.8, 10.9, 12.0),
    Section("W12x26", "Steel", 29000.0, 30.0, 204.0, 33.4, 26.0),
    Section("W14x22", "Steel", 29000.0, 30.0, 199.0, 29.0, 22.0),
    Section("W16x26", "Steel", 29000.0, 30.0, 301.0, 38.4, 26.0),
    Section("W18x35", "Steel", 29000.0, 30.0, 510.0, 57.6, 35.0),
    Section("W21x44", "Steel", 29000.0, 30.0, 843.0, 81.6, 44.0),
    Section("W24x55", "Steel", 29000.0, 30.0, 1350.0, 114.0, 55.0),
)

LUMBER_SECTIONS = (
    Section("2x8", "Lumber", 1600.0, 0.9, 47.63, 13.14),
    Section("2x10", "Lumber", 1600.0, 0.9, 98.93, 21.39),
    Section("2x12", "Lumber", 1600.0, 0.9, 177.98, 31.64),
)

SECTIONS: dict[Material, tuple[Section, ...]] = {
    "Steel": STEEL_SECTIONS,
    "Lumber": LUMBER_SECTIONS,
}


def section_by_name(material: Material, name: str) -> Section:
    for section in SECTIONS[material]:
        if section.name == name:
            return section
    raise ValueError(f"{name} is not a {material.lower()} section.")


def validate_beam(beam: BeamInput) -> Section:
    if not isfinite(beam.span) or not 4.0 <= beam.span <= 40.0:
        raise ValueError("Span must be between 4 and 40 ft.")
    if beam.support not in ("Simply supported", "Cantilever"):
        raise ValueError("Choose simply supported or cantilever supports.")
    if beam.deflection_limit not in (240, 360):
        raise ValueError("Deflection limit must be L/240 or L/360.")
    if beam.material not in SECTIONS:
        raise ValueError("Choose Steel or Lumber.")

    section = section_by_name(beam.material, beam.section)
    for load in beam.point_loads:
        if not isfinite(load.magnitude) or not 0.0 <= load.magnitude <= 100.0:
            raise ValueError("Point-load magnitude must be between 0 and 100 kips.")
        if not isfinite(load.position) or not 0.0 <= load.position <= beam.span:
            raise ValueError("Point-load position must be within the beam span.")
    for load in beam.uniform_loads:
        if not isfinite(load.magnitude) or not 0.0 <= load.magnitude <= 10.0:
            raise ValueError("Uniform-load magnitude must be between 0 and 10 kips/ft.")
        if not isfinite(load.start) or not isfinite(load.end):
            raise ValueError("Uniform-load positions must be finite numbers.")
        if not 0.0 <= load.start <= beam.span or not 0.0 <= load.end <= beam.span:
            raise ValueError("Uniform-load positions must be within the beam span.")
        if load.start > load.end:
            raise ValueError("Uniform-load start must not be after its end.")
    return section


def scale_load_positions(
    point_loads: Iterable[PointLoad],
    uniform_loads: Iterable[UniformLoad],
    old_span: float,
    new_span: float,
) -> tuple[tuple[PointLoad, ...], tuple[UniformLoad, ...]]:
    if old_span <= 0.0 or new_span <= 0.0:
        raise ValueError("Spans must be positive to scale load positions.")
    point_loads = tuple(point_loads)
    uniform_loads = tuple(uniform_loads)
    if any(
        not isfinite(load.magnitude) or not isfinite(load.position)
        for load in point_loads
    ):
        raise ValueError("Point-load values must be finite numbers.")
    if any(
        not isfinite(load.magnitude) or not isfinite(load.start) or not isfinite(load.end)
        for load in uniform_loads
    ):
        raise ValueError("Uniform-load values must be finite numbers.")
    factor = new_span / old_span
    scaled_points = tuple(
        PointLoad(load.magnitude, min(new_span, max(0.0, load.position * factor)))
        for load in point_loads
    )
    scaled_uniforms = tuple(
        UniformLoad(
            load.magnitude,
            min(new_span, max(0.0, load.start * factor)),
            min(new_span, max(0.0, load.end * factor)),
        )
        for load in uniform_loads
    )
    return scaled_points, scaled_uniforms


def analyze_beam(beam: BeamInput) -> Analysis:
    section = validate_beam(beam)
    reactions = _reactions(beam)
    boundaries = _boundaries(beam)
    moment_candidates = set(boundaries)
    shear_candidates = set(boundaries)

    for start, end in zip(boundaries, boundaries[1:]):
        if end - start <= 1e-12:
            continue
        middle = (start + end) / 2.0
        intensity = sum(
            load.magnitude
            for load in beam.uniform_loads
            if load.start < middle < load.end
        )
        start_shear = _shear_at(beam, reactions, start, "right")
        if intensity > 0.0:
            root = start + start_shear / intensity
            if start + 1e-10 < root < end - 1e-10:
                moment_candidates.add(root)

    max_shear_x, max_shear = max(
        (
            (x, abs(value))
            for x in shear_candidates
            for value in (
                _shear_at(beam, reactions, x, "left"),
                _shear_at(beam, reactions, x, "right"),
            )
        ),
        key=lambda item: item[1],
    )
    max_moment_x, max_moment_signed = max(
        ((x, _moment_at(beam, reactions, x)) for x in moment_candidates),
        key=lambda item: abs(item[1]),
    )
    deflection_at, deflection_roots = _deflection_function(beam, section, boundaries)
    deflection_candidates = set(_sample_coordinates(beam, boundaries))
    deflection_candidates.update(deflection_roots)
    max_deflection_x, max_deflection_signed = max(
        ((x, deflection_at(x)) for x in deflection_candidates),
        key=lambda item: abs(item[1]),
    )

    bending_stress = abs(max_moment_signed) * 12.0 / section.Sx
    deflection_allowable = beam.span * 12.0 / beam.deflection_limit
    bending_ratio = bending_stress / section.Fb
    deflection_ratio = abs(max_deflection_signed) / deflection_allowable
    recommendation = _recommendation(
        beam, section, abs(max_moment_signed), abs(max_deflection_signed)
    )

    plot_coordinates = sorted(deflection_candidates)
    samples = tuple(
        BeamSample(
            x=x,
            shear=_shear_at(beam, reactions, x, "right"),
            moment=_moment_at(beam, reactions, x),
            deflection=deflection_at(x),
        )
        for x in plot_coordinates
    )
    shear_curve = _shear_plot_points(beam, reactions, plot_coordinates)
    return Analysis(
        reactions=reactions,
        samples=samples,
        shear_curve=shear_curve,
        max_shear=max_shear,
        max_shear_x=max_shear_x,
        max_moment=abs(max_moment_signed),
        max_moment_x=max_moment_x,
        max_deflection=abs(max_deflection_signed),
        max_deflection_x=max_deflection_x,
        bending_stress=bending_stress,
        bending_allowable=section.Fb,
        bending_ratio=bending_ratio,
        bending_pass=bending_ratio <= 1.0,
        deflection_allowable=deflection_allowable,
        deflection_ratio=deflection_ratio,
        deflection_pass=deflection_ratio <= 1.0,
        recommendation=recommendation,
    )


def shear_at(beam: BeamInput, x: float, side: Literal["left", "right"] = "right") -> float:
    validate_beam(beam)
    return _shear_at(beam, _reactions(beam), x, side)


def moment_at(beam: BeamInput, x: float) -> float:
    validate_beam(beam)
    return _moment_at(beam, _reactions(beam), x)


def deflection_at(beam: BeamInput, x: float) -> float:
    section = validate_beam(beam)
    evaluate, _ = _deflection_function(beam, section, _boundaries(beam))
    if not 0.0 <= x <= beam.span:
        raise ValueError("Position must be within the beam span.")
    return evaluate(x)


def _reactions(beam: BeamInput) -> Reactions:
    total = sum(load.magnitude for load in beam.point_loads)
    moment_about_left = sum(
        load.magnitude * load.position for load in beam.point_loads
    )
    for load in beam.uniform_loads:
        resultant = load.magnitude * (load.end - load.start)
        total += resultant
        moment_about_left += resultant * (load.start + load.end) / 2.0
    if beam.support == "Cantilever":
        return Reactions(total, 0.0, moment_about_left)
    left = (total * beam.span - moment_about_left) / beam.span
    return Reactions(left, total - left, 0.0)


def _shear_at(
    beam: BeamInput,
    reactions: Reactions,
    x: float,
    side: Literal["left", "right"],
) -> float:
    if not 0.0 <= x <= beam.span:
        raise ValueError("Position must be within the beam span.")
    shear = reactions.left
    for load in beam.point_loads:
        if load.position < x or (side == "right" and load.position == x):
            shear -= load.magnitude
    for load in beam.uniform_loads:
        shear -= load.magnitude * max(0.0, min(x, load.end) - load.start)
    return shear


def _moment_at(beam: BeamInput, reactions: Reactions, x: float) -> float:
    if not 0.0 <= x <= beam.span:
        raise ValueError("Position must be within the beam span.")
    if beam.support == "Cantilever":
        moment = 0.0
        for load in beam.point_loads:
            if load.position > x:
                moment -= load.magnitude * (load.position - x)
        for load in beam.uniform_loads:
            start = max(load.start, x)
            if load.end > start:
                resultant = load.magnitude * (load.end - start)
                moment -= resultant * ((start + load.end) / 2.0 - x)
        return moment

    moment = reactions.left * x
    for load in beam.point_loads:
        if x >= load.position:
            moment -= load.magnitude * (x - load.position)
    for load in beam.uniform_loads:
        end = min(x, load.end)
        if end > load.start:
            resultant = load.magnitude * (end - load.start)
            moment -= resultant * (x - (load.start + end) / 2.0)
    return moment


def _boundaries(beam: BeamInput) -> list[float]:
    return sorted(
        {0.0, beam.span}
        | {load.position for load in beam.point_loads}
        | {load.start for load in beam.uniform_loads}
        | {load.end for load in beam.uniform_loads}
    )


def _sample_coordinates(beam: BeamInput, boundaries: Iterable[float]) -> set[float]:
    count = int(beam.span * 2)
    coordinates = {beam.span * index / count for index in range(count + 1)}
    coordinates.update(boundaries)
    return coordinates


def _shear_plot_points(
    beam: BeamInput,
    reactions: Reactions,
    coordinates: Iterable[float],
) -> tuple[tuple[float, float], ...]:
    points: list[tuple[float, float]] = []
    point_positions = {load.position for load in beam.point_loads}
    for x in sorted(coordinates):
        if x == 0.0:
            points.append((x, 0.0))
        if x in point_positions:
            points.append((x, _shear_at(beam, reactions, x, "left")))
        points.append((x, _shear_at(beam, reactions, x, "right")))
    return tuple(points)


@dataclass(frozen=True)
class _DeflectionInterval:
    x0: float
    length: float
    a: float
    b: float
    c: float
    y0: float
    slope0: float
    EI: float

    def evaluate(self, local_x: float) -> tuple[float, float]:
        s = local_x
        curvature_integral = (
            self.a * s**3 / 3.0 + self.b * s**2 / 2.0 + self.c * s
        ) / self.EI
        deflection_integral = (
            self.a * s**4 / 12.0
            + self.b * s**3 / 6.0
            + self.c * s**2 / 2.0
        ) / self.EI
        return (
            self.y0 + self.slope0 * s + deflection_integral,
            self.slope0 + curvature_integral,
        )


def _deflection_function(
    beam: BeamInput,
    section: Section,
    boundaries: list[float],
) -> tuple[callable, set[float]]:
    EI = section.E * section.Ix
    lengths_in = [(end - start) * 12.0 for start, end in zip(boundaries, boundaries[1:])]

    def integrate(initial_slope: float) -> list[_DeflectionInterval]:
        y = 0.0
        slope = initial_slope
        intervals: list[_DeflectionInterval] = []
        for start, length in zip(boundaries, lengths_in):
            if length <= 1e-12:
                continue
            x0 = start * 12.0
            moment0 = _moment_at(beam, _reactions(beam), start) * 12.0
            moment_mid = _moment_at(beam, _reactions(beam), start + length / 24.0) * 12.0
            moment_end = _moment_at(beam, _reactions(beam), start + length / 12.0) * 12.0
            a = 2.0 * (moment0 + moment_end - 2.0 * moment_mid) / length**2
            b = (moment_end - moment0 - a * length**2) / length
            interval = _DeflectionInterval(
                x0=x0, length=length, a=a, b=b, c=moment0,
                y0=y, slope0=slope, EI=EI,
            )
            intervals.append(interval)
            y, slope = interval.evaluate(length)
        return intervals

    intervals = integrate(0.0)
    if beam.support == "Simply supported":
        total_length = beam.span * 12.0
        initial_slope = -intervals[-1].evaluate(intervals[-1].length)[0] / total_length
        intervals = integrate(initial_slope)

    def evaluate(x_feet: float) -> float:
        x_in = x_feet * 12.0
        for interval in intervals:
            if interval.x0 - 1e-9 <= x_in <= interval.x0 + interval.length + 1e-9:
                y, _ = interval.evaluate(min(interval.length, max(0.0, x_in - interval.x0)))
                return y
        return 0.0

    extrema: set[float] = {0.0, beam.span}
    for interval in intervals:
        critical = [0.0, interval.length]
        critical.extend(
            root for root in _quadratic_roots(interval.a, interval.b, interval.c)
            if 1e-10 < root < interval.length - 1e-10
        )
        critical.sort()
        for left, right in zip(critical, critical[1:]):
            _, left_slope = interval.evaluate(left)
            _, right_slope = interval.evaluate(right)
            if abs(left_slope) <= 1e-12:
                extrema.add((interval.x0 + left) / 12.0)
            if left_slope * right_slope < 0.0:
                lo, hi = left, right
                sign = copysign(1.0, left_slope)
                for _ in range(60):
                    mid = (lo + hi) / 2.0
                    _, mid_slope = interval.evaluate(mid)
                    if copysign(1.0, mid_slope) == sign:
                        lo = mid
                    else:
                        hi = mid
                extrema.add((interval.x0 + (lo + hi) / 2.0) / 12.0)
        if abs(interval.evaluate(interval.length)[1]) <= 1e-12:
            extrema.add((interval.x0 + interval.length) / 12.0)
    return evaluate, extrema


def _quadratic_roots(a: float, b: float, c: float) -> list[float]:
    scale = max(abs(a), abs(b), abs(c), 1.0)
    tolerance = 1e-14 * scale
    if abs(a) <= tolerance:
        if abs(b) <= tolerance:
            return []
        return [-c / b]
    discriminant = b * b - 4.0 * a * c
    if discriminant < -tolerance:
        return []
    if abs(discriminant) <= tolerance:
        return [-b / (2.0 * a)]
    root = sqrt(discriminant)
    return [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]


def _recommendation(
    beam: BeamInput,
    selected: Section,
    max_moment: float,
    max_deflection: float,
) -> Section | None:
    allowable_deflection = beam.span * 12.0 / beam.deflection_limit
    passing = []
    for section in SECTIONS[beam.material]:
        stress = max_moment * 12.0 / section.Sx
        scaled_deflection = max_deflection * (selected.E * selected.Ix) / (
            section.E * section.Ix
        )
        if stress <= section.Fb and scaled_deflection <= allowable_deflection:
            passing.append(section)
    if beam.material == "Steel":
        return min(
            passing,
            key=lambda item: (item.weight or float("inf"), -(item.Ix)),
            default=None,
        )
    return passing[0] if passing else None
