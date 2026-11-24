"""Calculation-sheet PDF export using Matplotlib."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyArrowPatch, Rectangle

from beam_calculations import Analysis, BeamInput


BLUE = "#2563eb"
INK = "#172033"
MUTED = "#677287"
GREEN = "#16855b"
AMBER = "#c78316"
RED = "#d14a4a"


def _format_loads(beam: BeamInput) -> list[str]:
    lines = ["Loads:"]
    if beam.point_loads:
        lines.extend(
            f"  Point: {load.magnitude:g} k at {load.position:g} ft"
            for load in beam.point_loads
        )
    else:
        lines.append("  Point: none")
    if beam.uniform_loads:
        lines.extend(
            f"  Uniform: {load.magnitude:g} k/ft from {load.start:g} to {load.end:g} ft"
            for load in beam.uniform_loads
        )
    else:
        lines.append("  Uniform: none")
    return lines


def analysis_to_pdf(
    path: str | Path,
    beam: BeamInput,
    analysis: Analysis,
) -> None:
    destination = Path(path)
    with PdfPages(destination) as pdf:
        fig = plt.figure(figsize=(11, 8.5), facecolor="white")
        fig.suptitle("Beam Designer Calculation Sheet", x=0.06, y=0.97,
                     ha="left", fontsize=16, fontweight="bold", color=INK)

        inputs = (
            f"Support: {beam.support}    "
            f"Span: {beam.span:g} ft    "
            f"Material: {beam.material}    "
            f"Section: {beam.section}    "
            f"Deflection limit: L/{beam.deflection_limit}"
        )
        fig.text(0.06, 0.925, inputs, ha="left", va="top",
                 fontsize=9.5, color=INK)

        load_lines = _format_loads(beam)
        fig.text(
            0.06,
            0.885,
            "\n".join(load_lines),
            ha="left",
            va="top",
            fontsize=8.5,
            color=MUTED,
            linespacing=1.45,
        )

        reaction_text = (
            f"Reactions: left {analysis.reactions.left:.3f} k upward"
            + (
                f"; right {analysis.reactions.right:.3f} k upward"
                if beam.support == "Simply supported"
                else f"; fixed moment {analysis.reactions.fixed_moment:.3f} kip-ft"
            )
        )
        fig.text(0.63, 0.885, reaction_text, ha="left", va="top",
                 fontsize=9, color=INK)

        beam_ax = fig.add_axes([0.06, 0.66, 0.88, 0.16])
        beam_ax.set_xlim(-0.5, beam.span + 0.5)
        beam_ax.set_ylim(-1.15, 1.45)
        beam_ax.axis("off")
        beam_ax.plot([0, beam.span], [0, 0], color=BLUE, linewidth=7,
                     solid_capstyle="round")
        if beam.support == "Cantilever":
            beam_ax.add_patch(Rectangle((-0.28, -0.30), 0.28, 0.60,
                                        facecolor="#dbeafe",
                                        edgecolor=BLUE, linewidth=1.5))
            beam_ax.text(-0.12, -0.55, "Fixed", ha="center", va="top",
                         fontsize=8, color=MUTED)
        else:
            for x in (0, beam.span):
                triangle = beam_ax.fill(
                    [x - 0.35, x + 0.35, x],
                    [-0.02, -0.02, -0.28],
                    facecolor="#dbeafe",
                    edgecolor=BLUE,
                )
            beam_ax.text(0, -0.48, "Pinned", ha="center", va="top",
                         fontsize=8, color=MUTED)
            beam_ax.text(beam.span, -0.48, "Roller", ha="center", va="top",
                         fontsize=8, color=MUTED)

        for load in beam.point_loads:
            if load.magnitude == 0:
                continue
            beam_ax.add_patch(FancyArrowPatch(
                (load.position, 0.95),
                (load.position, 0.10),
                arrowstyle="-|>",
                mutation_scale=11 + 7 * (load.magnitude / 100) ** 0.5,
                linewidth=1.2,
                color=RED,
            ))
            beam_ax.text(load.position, 1.02, f"{load.magnitude:g} k",
                         ha="center", va="bottom", fontsize=8, color=INK)

        for load in beam.uniform_loads:
            if load.magnitude == 0 or load.start == load.end:
                continue
            length = 0.35 + 0.55 * (load.magnitude / 10) ** 0.5
            count = max(3, int((load.end - load.start) * 2))
            for index in range(count + 1):
                x = load.start + (load.end - load.start) * index / count
                beam_ax.add_patch(FancyArrowPatch(
                    (x, length),
                    (x, 0.10),
                    arrowstyle="-|>",
                    mutation_scale=8 + 7 * (load.magnitude / 10) ** 0.5,
                    linewidth=1,
                    color=MUTED,
                ))
            beam_ax.text(
                (load.start + load.end) / 2,
                length + 0.07,
                f"{load.magnitude:g} k/ft",
                ha="center",
                va="bottom",
                fontsize=8,
                color=INK,
            )

        beam_ax.text(beam.span / 2, -0.72, f"{beam.span:g} ft",
                     ha="center", va="top", fontsize=9, color=MUTED)

        plot_specs = (
            ("Shear V (kips)", "shear", BLUE),
            ("Moment M (kip-ft)", "moment", "#818cf8"),
            ("Deflection y (in)", "deflection", "#d18b00"),
        )
        for index, (title, attribute, color) in enumerate(plot_specs):
            left = 0.06
            bottom = 0.48 - index * 0.145
            ax = fig.add_axes([left, bottom, 0.88, 0.105])
            x = [sample.x for sample in analysis.samples]
            y = [
                getattr(sample, attribute)
                for sample in analysis.samples
            ]
            ax.plot(x, y, color=color, linewidth=1.7)
            ax.axhline(0, color="#dde3ec", linewidth=0.8)
            ax.fill_between(x, y, 0, color=color, alpha=0.20)
            ax.set_title(title, loc="left", fontsize=9, color=INK, pad=3)
            ax.tick_params(labelsize=7, colors=MUTED)
            ax.grid(True, axis="x", color="#edf0f5", linewidth=0.5)
            if attribute == "shear":
                max_x = analysis.max_shear_x
                max_value = analysis.max_shear
                scatter_value = next(
                    sample.shear for sample in analysis.samples
                    if abs(sample.x - max_x) == min(
                        abs(candidate.x - max_x) for candidate in analysis.samples
                    )
                )
            elif attribute == "moment":
                max_x = analysis.max_moment_x
                max_value = analysis.max_moment
                scatter_value = next(
                    sample.moment for sample in analysis.samples
                    if abs(sample.x - max_x) == min(
                        abs(candidate.x - max_x) for candidate in analysis.samples
                    )
                )
            else:
                max_x = analysis.max_deflection_x
                max_value = analysis.max_deflection
                scatter_value = next(
                    sample.deflection for sample in analysis.samples
                    if abs(sample.x - max_x) == min(
                        abs(candidate.x - max_x) for candidate in analysis.samples
                    )
                )
            ax.scatter([max_x], [scatter_value], s=18, color=RED, zorder=4)
            ax.text(
                0.99,
                1.14,
                f"Max: {max_value:.3f} @ {max_x:.2f} ft",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                color=INK,
            )

        card_y = 0.035
        cards = (
            (
                "BENDING",
                f"fb = {analysis.bending_stress:.3f} ksi",
                f"Fb = {analysis.bending_allowable:.3f} ksi",
                "PASS" if analysis.bending_pass else "FAIL",
                analysis.bending_ratio,
            ),
            (
                "DEFLECTION",
                f"|y|max = {analysis.max_deflection:.4f} in",
                f"Allowable = {analysis.deflection_allowable:.4f} in",
                "PASS" if analysis.deflection_pass else "FAIL",
                analysis.deflection_ratio,
            ),
        )
        for index, (title, actual, allowable, status, ratio) in enumerate(cards):
            x = 0.06 + index * 0.44
            fig.patches.append(
                Rectangle(
                    (x, card_y),
                    0.40,
                    0.105,
                    transform=fig.transFigure,
                    facecolor="white",
                    edgecolor="#dde3ec",
                    linewidth=1,
                )
            )
            fig.text(x + 0.015, card_y + 0.082, title, fontsize=8.5,
                     fontweight="bold", color=MUTED)
            fig.text(x + 0.015, card_y + 0.055, actual, fontsize=9,
                     fontweight="bold", color=INK)
            fig.text(x + 0.015, card_y + 0.030, allowable, fontsize=8,
                     color=MUTED)
            color = GREEN if status == "PASS" else RED
            fig.text(x + 0.355, card_y + 0.055, status, fontsize=9,
                     fontweight="bold", color=color, ha="right")
            bar_color = GREEN if ratio < 0.7 else AMBER if ratio <= 1.0 else RED
            fig.patches.append(
                Rectangle(
                    (x + 0.015, card_y + 0.012),
                    0.35,
                    0.012,
                    transform=fig.transFigure,
                    facecolor="#edf0f5",
                    edgecolor="none",
                )
            )
            fig.patches.append(
                Rectangle(
                    (x + 0.015, card_y + 0.012),
                    0.35 * min(ratio, 1.0),
                    0.012,
                    transform=fig.transFigure,
                    facecolor=bar_color,
                    edgecolor="none",
                )
            )

        recommendation = (
            f"Lightest passing section: {analysis.recommendation.name}"
            if analysis.recommendation
            else "No passing section."
        )
        fig.text(0.94, card_y + 0.095, recommendation, ha="right", va="bottom",
                 fontsize=8.5, color=INK)

        pdf.savefig(fig, facecolor="white")
        plt.close(fig)
