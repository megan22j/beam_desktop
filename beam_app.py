"""Tkinter interface for the Beam Designer."""

from math import sqrt
import tkinter as tk
from tkinter import ttk
from typing import Any

from beam_calculations import (
    Analysis,
    BeamInput,
    LUMBER_SECTIONS,
    PointLoad,
    SECTIONS,
    STEEL_SECTIONS,
    UniformLoad,
    analyze_beam,
    deflection_at,
    moment_at,
    scale_load_positions,
    shear_at,
)


BLUE = "#2563eb"
BLUE_DARK = "#1d4ed8"
INK = "#172033"
MUTED = "#677287"
LINE = "#dde3ec"
BACKGROUND = "#f4f6fa"
GREEN = "#16855b"
AMBER = "#c78316"
RED = "#d14a4a"


class BeamDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Beam Designer")
        self.root.geometry("1320x900")
        self.root.minsize(1000, 700)
        self.root.configure(background=BACKGROUND)

        self.span_var = tk.StringVar(value="20")
        self.support_var = tk.StringVar(value="Simply supported")
        self.material_var = tk.StringVar(value="Steel")
        self.section_var = tk.StringVar(value="W12x26")
        self.limit_var = tk.StringVar(value="L/360")
        self.slider_var = tk.DoubleVar(value=20.0)
        self.error_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self._suspend_refresh = False
        self._scaling_span = False
        self._span_source = 20.0
        self._span_source_points: tuple[PointLoad, ...] = ()
        self._span_source_uniforms: tuple[UniformLoad, ...] = (
            UniformLoad(1.0, 0.0, 20.0),
        )
        self._point_rows: list[dict[str, Any]] = []
        self._uniform_rows: list[dict[str, Any]] = []
        self._point_markers: list[tuple[float, int]] = []
        self._dragging_point: int | None = None
        self._hover_x: float | None = None
        self._analysis: Analysis | None = None
        self._beam: BeamInput | None = None

        self._configure_styles()
        self._build_header()
        self._build_layout()
        self._add_uniform_load(UniformLoad(1.0, 0.0, 20.0), refresh=False)
        self._set_span_snapshot()
        self._watch_inputs()
        self._refresh()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.configure("TFrame", background=BACKGROUND)
        style.configure("Card.TFrame", background="white")
        style.configure("TLabel", background=BACKGROUND, foreground=INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="white", foreground=INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="white", foreground=INK, font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", background="white", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Section.TLabel", background="white", foreground=MUTED, font=("Segoe UI", 9, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"))
        style.configure("TEntry", padding=5)

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, style="Card.TFrame", padding=(20, 12))
        header.pack(fill="x")
        ttk.Label(header, text="BEAM", foreground="white", background=BLUE, padding=(9, 6),
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 12))
        title_box = ttk.Frame(header, style="Card.TFrame")
        title_box.pack(side="left")
        ttk.Label(title_box, text="Beam Designer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Beam analysis and section checks", style="Muted.TLabel").pack(anchor="w")

    def _build_layout(self) -> None:
        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=14, pady=14)

        sidebar_outer = ttk.Frame(panes, width=350)
        sidebar_outer.pack_propagate(False)
        sidebar_canvas = tk.Canvas(sidebar_outer, background=BACKGROUND, highlightthickness=0, width=350)
        sidebar_scroll = ttk.Scrollbar(sidebar_outer, orient="vertical", command=sidebar_canvas.yview)
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_scroll.pack(side="right", fill="y")
        self.sidebar = ttk.Frame(sidebar_canvas, padding=(3, 2, 12, 12))
        sidebar_window = sidebar_canvas.create_window((0, 0), window=self.sidebar, anchor="nw")
        self.sidebar.bind(
            "<Configure>",
            lambda _event: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")),
        )
        sidebar_canvas.bind(
            "<Configure>",
            lambda event: sidebar_canvas.itemconfigure(sidebar_window, width=event.width),
        )
        panes.add(sidebar_outer, weight=0)

        workspace = ttk.Frame(panes, padding=(12, 2, 2, 2))
        panes.add(workspace, weight=1)

        self._build_inputs(self.sidebar)
        self._build_workspace(workspace)

    def _build_inputs(self, parent: ttk.Frame) -> None:
        self._input_card(parent, "Beam")
        self._field_label(parent, "Support type")
        support = ttk.Frame(parent)
        support.pack(fill="x", pady=(0, 10))
        for value, label in (("Simply supported", "Simply supported"), ("Cantilever", "Cantilever")):
            ttk.Radiobutton(
                support, text=label, value=value, variable=self.support_var,
                command=self._refresh,
            ).pack(side="left", padx=(0, 8))

        self._field_label(parent, "Span (ft)")
        span_row = ttk.Frame(parent)
        span_row.pack(fill="x")
        self.span_entry = ttk.Entry(span_row, textvariable=self.span_var, width=9)
        self.span_entry.pack(side="left")
        self.span_entry.bind("<Return>", lambda _event: self._commit_span())
        self.span_entry.bind("<FocusOut>", lambda _event: self._commit_span())
        ttk.Label(span_row, text="4 to 40 ft").pack(side="left", padx=8)
        ttk.Scale(
            parent, from_=4.0, to=40.0, variable=self.slider_var,
            command=self._on_slider_change,
        ).pack(fill="x", pady=(6, 12))

        self._input_card(parent, "Loads")
        self.load_list = ttk.Frame(parent)
        self.load_list.pack(fill="x")
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(8, 14))
        ttk.Button(actions, text="+ Point load", command=self._add_point_load).pack(side="left")
        ttk.Button(actions, text="+ Uniform load", command=self._add_uniform_load).pack(side="left", padx=6)

        self._input_card(parent, "Material and section")
        self._field_label(parent, "Material")
        material = ttk.Combobox(
            parent, textvariable=self.material_var, values=("Steel", "Lumber"),
            state="readonly",
        )
        material.pack(fill="x", pady=(0, 9))
        material.bind("<<ComboboxSelected>>", self._on_material_changed)
        self._field_label(parent, "Section")
        self.section_combo = ttk.Combobox(parent, textvariable=self.section_var, state="readonly")
        self.section_combo.pack(fill="x", pady=(0, 12))
        self.section_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh())
        self._update_section_options()

        self._input_card(parent, "Deflection limit")
        ttk.Combobox(
            parent, textvariable=self.limit_var, values=("L/240", "L/360"),
            state="readonly",
        ).pack(fill="x", pady=(0, 10))
        self.limit_var.trace_add("write", lambda *_args: self._refresh())
        self.error_label = ttk.Label(parent, textvariable=self.error_var, foreground=RED, wraplength=310)
        self.error_label.pack(fill="x", pady=(2, 6))
        ttk.Label(
            parent, textvariable=self.status_var, foreground=MUTED, wraplength=310,
        ).pack(fill="x", pady=(0, 8))

    def _build_workspace(self, parent: ttk.Frame) -> None:
        drawing_card = ttk.Frame(parent, style="Card.TFrame", padding=8)
        drawing_card.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(
            drawing_card, background="white", highlightthickness=0,
            height=540, takefocus=True,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Leave>", self._on_canvas_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        checks = ttk.Frame(parent)
        checks.pack(fill="x", pady=(12, 0))
        self.bending_card = self._check_card(checks, "Bending", "fb / Fb")
        self.deflection_card = self._check_card(checks, "Deflection", "|y|max / allowable")
        self.bending_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.deflection_card.pack(side="left", fill="both", expand=True, padx=(6, 0))

        recommendation = ttk.Frame(parent, style="Card.TFrame", padding=(12, 9))
        recommendation.pack(fill="x", pady=(10, 0))
        self.recommendation_var = tk.StringVar(value="")
        ttk.Label(recommendation, textvariable=self.recommendation_var, style="Card.TLabel").pack(side="left")
        self.use_section_button = ttk.Button(
            recommendation, text="Use section", command=self._use_recommended_section,
        )

    def _check_card(self, parent: ttk.Frame, title: str, formula: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(12, 10))
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w")
        actual = ttk.Label(card, text="--", style="Card.TLabel", font=("Segoe UI", 13, "bold"))
        actual.pack(anchor="w", pady=(4, 0))
        allowable = ttk.Label(card, text="Allowable: --", style="Muted.TLabel")
        allowable.pack(anchor="w")
        bar = tk.Canvas(card, height=10, background="#edf0f5", highlightthickness=0)
        bar.pack(fill="x", pady=(8, 4))
        status = ttk.Label(card, text="--", style="Card.TLabel", font=("Segoe UI", 9, "bold"))
        status.pack(anchor="w")
        card.widgets = {"actual": actual, "allowable": allowable, "bar": bar, "status": status}  # type: ignore[attr-defined]
        tooltip_text = (
            "Bending: fb = |M|max x 12 / Sx; pass when fb <= Fb."
            if title == "Bending"
            else "Deflection: |y|max / (L / limit); pass when |y|max <= L / limit."
        )
        for widget in (card, actual, allowable, bar, status):
            widget.bind("<Enter>", lambda _event, text=tooltip_text: self._show_tooltip(text))
            widget.bind("<Leave>", lambda _event: self._hide_tooltip())
        return card

    def _input_card(self, parent: ttk.Frame, title: str) -> None:
        ttk.Label(parent, text=title.upper(), style="Section.TLabel").pack(anchor="w", pady=(12, 8))

    def _field_label(self, parent: ttk.Frame, text: str) -> None:
        ttk.Label(parent, text=text, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    def _watch_inputs(self) -> None:
        self.span_var.trace_add("write", self._on_span_entry_change)
        self.support_var.trace_add("write", lambda *_args: self._refresh())

    def _add_point_load(self, load: PointLoad | None = None, refresh: bool = True) -> None:
        span = self._current_span_or_default()
        if load is None:
            load = PointLoad(1.0, span if self.support_var.get() == "Cantilever" else span / 2.0)
        row = ttk.Frame(self.load_list, style="Card.TFrame", padding=(7, 7))
        row.pack(fill="x", pady=(0, 6))
        magnitude = tk.StringVar(value=self._fmt(load.magnitude))
        position = tk.StringVar(value=self._fmt(load.position))
        ttk.Label(row, text="Point (k)", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(row, text="at (ft)", style="Card.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Entry(row, textvariable=magnitude, width=7).grid(row=1, column=0, sticky="ew")
        ttk.Entry(row, textvariable=position, width=7).grid(row=1, column=1, sticky="ew", padx=(6, 0))
        index = len(self._point_rows)
        ttk.Button(row, text="Remove", width=8, command=lambda: self._remove_load("point", index)).grid(
            row=0, column=2, rowspan=2, padx=(8, 0),
        )
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        record = {"frame": row, "magnitude": magnitude, "position": position}
        self._point_rows.append(record)
        for variable in (magnitude, position):
            variable.trace_add("write", lambda *_args: self._on_load_changed())
        self._refresh_baseline()
        if refresh:
            self._refresh()

    def _add_uniform_load(self, load: UniformLoad | None = None, refresh: bool = True) -> None:
        span = self._current_span_or_default()
        if load is None:
            load = UniformLoad(1.0, 0.0, span)
        row = ttk.Frame(self.load_list, style="Card.TFrame", padding=(7, 7))
        row.pack(fill="x", pady=(0, 6))
        magnitude = tk.StringVar(value=self._fmt(load.magnitude))
        start = tk.StringVar(value=self._fmt(load.start))
        end = tk.StringVar(value=self._fmt(load.end))
        for column, label in enumerate(("Uniform (k/ft)", "start (ft)", "end (ft)")):
            ttk.Label(row, text=label, style="Card.TLabel").grid(row=0, column=column, sticky="w")
        for column, variable in enumerate((magnitude, start, end)):
            ttk.Entry(row, textvariable=variable, width=7).grid(
                row=1, column=column, sticky="ew", padx=(0 if column == 0 else 5, 0),
            )
        index = len(self._uniform_rows)
        ttk.Button(row, text="X", width=3, command=lambda: self._remove_load("uniform", index)).grid(
            row=0, column=3, rowspan=2, padx=(6, 0),
        )
        for column in range(3):
            row.columnconfigure(column, weight=1)
        record = {"frame": row, "magnitude": magnitude, "start": start, "end": end}
        self._uniform_rows.append(record)
        for variable in (magnitude, start, end):
            variable.trace_add("write", lambda *_args: self._on_load_changed())
        self._refresh_baseline()
        if refresh:
            self._refresh()

    def _remove_load(self, kind: str, index: int) -> None:
        rows = self._point_rows if kind == "point" else self._uniform_rows
        if not 0 <= index < len(rows):
            return
        rows.pop(index)["frame"].destroy()
        self._renumber_load_buttons()
        self._refresh_baseline()
        self._refresh()

    def _renumber_load_buttons(self) -> None:
        for kind, rows in (("point", self._point_rows), ("uniform", self._uniform_rows)):
            for index, record in enumerate(rows):
                button = record["frame"].winfo_children()[-1]
                button.configure(command=lambda k=kind, i=index: self._remove_load(k, i))

    def _on_material_changed(self, _event: tk.Event[Any]) -> None:
        material = self.material_var.get()
        self.section_var.set("W12x26" if material == "Steel" else "2x10")
        self._update_section_options()
        self._refresh()

    def _update_section_options(self) -> None:
        sections = STEEL_SECTIONS if self.material_var.get() == "Steel" else LUMBER_SECTIONS
        self.section_combo.configure(values=tuple(section.name for section in sections))

    def _on_span_entry_change(self, *_args: Any) -> None:
        if self._suspend_refresh or self._scaling_span:
            return
        try:
            span = float(self.span_var.get())
        except ValueError:
            self.error_var.set("Enter a span from 4 to 40 ft.")
            self._clear_analysis()
            return
        if not 4.0 <= span <= 40.0:
            self.error_var.set("Span must be between 4 and 40 ft.")
            self._clear_analysis()
            return
        self.slider_var.set(span)
        self._apply_span(span, commit=False)

    def _on_slider_change(self, value: str) -> None:
        if self._suspend_refresh:
            return
        span = round(float(value) * 10.0) / 10.0
        self._suspend_refresh = True
        self.span_var.set(self._fmt(span))
        self._suspend_refresh = False
        self._apply_span(span, commit=True)

    def _commit_span(self) -> None:
        try:
            span = float(self.span_var.get())
        except ValueError:
            return
        if 4.0 <= span <= 40.0:
            self._apply_span(span, commit=True)

    def _apply_span(self, span: float, commit: bool) -> None:
        if self._span_source <= 0.0:
            return
        try:
            self._read_point_loads()
            self._read_uniform_loads()
        except ValueError:
            self._refresh()
            return
        try:
            points, uniforms = scale_load_positions(
                self._span_source_points,
                self._span_source_uniforms,
                self._span_source,
                span,
            )
        except ValueError as error:
            self.error_var.set(str(error))
            self._clear_analysis()
            return
        self._scaling_span = True
        self._suspend_refresh = True
        self._set_load_values(points, uniforms)
        self._suspend_refresh = False
        self._scaling_span = False
        self.error_var.set("")
        if commit:
            self._set_span_snapshot(span, points, uniforms)
        self._refresh()

    def _set_span_snapshot(
        self,
        span: float | None = None,
        points: tuple[PointLoad, ...] | None = None,
        uniforms: tuple[UniformLoad, ...] | None = None,
    ) -> None:
        self._span_source = span if span is not None else self._current_span_or_default()
        self._span_source_points = points if points is not None else self._read_point_loads()
        self._span_source_uniforms = uniforms if uniforms is not None else self._read_uniform_loads()

    def _refresh_baseline(self) -> None:
        if not self._scaling_span:
            try:
                self._set_span_snapshot()
            except ValueError:
                pass

    def _on_load_changed(self) -> None:
        self._refresh_baseline()
        self._refresh()

    def _set_load_values(
        self,
        points: tuple[PointLoad, ...],
        uniforms: tuple[UniformLoad, ...],
    ) -> None:
        for row, load in zip(self._point_rows, points):
            row["position"].set(self._fmt(load.position))
        for row, load in zip(self._uniform_rows, uniforms):
            row["start"].set(self._fmt(load.start))
            row["end"].set(self._fmt(load.end))

    def _read_point_loads(self) -> tuple[PointLoad, ...]:
        return tuple(
            PointLoad(float(row["magnitude"].get()), float(row["position"].get()))
            for row in self._point_rows
        )

    def _read_uniform_loads(self) -> tuple[UniformLoad, ...]:
        return tuple(
            UniformLoad(
                float(row["magnitude"].get()),
                float(row["start"].get()),
                float(row["end"].get()),
            )
            for row in self._uniform_rows
        )

    def _build_beam(self) -> BeamInput:
        span = float(self.span_var.get())
        return BeamInput(
            span=span,
            support=self.support_var.get(),  # type: ignore[arg-type]
            point_loads=self._read_point_loads(),
            uniform_loads=self._read_uniform_loads(),
            material=self.material_var.get(),  # type: ignore[arg-type]
            section=self.section_var.get(),
            deflection_limit=240 if self.limit_var.get() == "L/240" else 360,
        )

    def _refresh(self) -> None:
        if self._suspend_refresh:
            return
        try:
            beam = self._build_beam()
            analysis = analyze_beam(beam)
        except (ValueError, OverflowError) as error:
            self.error_var.set(str(error))
            self._clear_analysis()
            return
        self.error_var.set("")
        self._beam = beam
        self._analysis = analysis
        self.status_var.set("All results use the current inputs.")
        self._update_checks(analysis)
        self._update_recommendation(analysis)
        self._draw()

    def _clear_analysis(self) -> None:
        self._analysis = None
        self._beam = None
        self.status_var.set("Fix the input error to update the analysis.")
        self._update_checks(None)
        self._update_recommendation(None)
        self._draw()

    def _update_checks(self, result: Analysis | None) -> None:
        if result is None:
            self._set_check_card(self.bending_card, "--", "Allowable: --", None, None)
            self._set_check_card(self.deflection_card, "--", "Allowable: --", None, None)
            return
        self._set_check_card(
            self.bending_card,
            f"{result.bending_stress:.2f} ksi",
            f"Allowable: {result.bending_allowable:.2f} ksi",
            result.bending_ratio,
            result.bending_pass,
        )
        self._set_check_card(
            self.deflection_card,
            f"{result.max_deflection:.3f} in",
            f"Allowable: {result.deflection_allowable:.3f} in",
            result.deflection_ratio,
            result.deflection_pass,
        )

    def _set_check_card(
        self,
        card: ttk.Frame,
        actual: str,
        allowable: str,
        ratio: float | None,
        passed: bool | None,
    ) -> None:
        widgets = card.widgets  # type: ignore[attr-defined]
        widgets["actual"].configure(text=actual)
        widgets["allowable"].configure(text=allowable)
        widgets["status"].configure(
            text="PASS" if passed else "FAIL" if passed is False else "--",
            foreground=GREEN if passed else RED if passed is False else MUTED,
        )
        bar: tk.Canvas = widgets["bar"]
        bar.delete("all")
        bar.update_idletasks()
        width = max(bar.winfo_width(), 40)
        bar.create_rectangle(0, 0, width, 10, fill="#edf0f5", outline="")
        if ratio is not None:
            fill = GREEN if ratio < 0.7 else AMBER if ratio <= 1.0 else RED
            bar.create_rectangle(0, 0, width * min(ratio, 1.0), 10, fill=fill, outline="")

    def _update_recommendation(self, result: Analysis | None) -> None:
        if result is None:
            self.recommendation_var.set("No current section recommendation")
            self.use_section_button.pack_forget()
        elif result.recommendation is None:
            self.recommendation_var.set("No passing section.")
            self.use_section_button.pack_forget()
        else:
            self.recommendation_var.set(f"Lightest passing section: {result.recommendation.name}")
            if not self.use_section_button.winfo_manager():
                self.use_section_button.pack(side="right")

    def _use_recommended_section(self) -> None:
        if self._analysis and self._analysis.recommendation:
            self.section_var.set(self._analysis.recommendation.name)
            self._refresh()

    def _draw(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 480)
        height = max(self.canvas.winfo_height(), 480)
        span = self._beam.span if self._beam else self._current_span_or_default()
        left, right = self._beam_x_bounds(span, width)
        x_map = lambda x: left + x / span * (right - left)
        beam_y = 63.0
        self._draw_title("BEAM AND LOADS", 12, 18)
        if self._analysis is None or self._beam is None:
            self._draw_placeholder(left, right, beam_y, height)
            return

        beam = self._beam
        analysis = self._analysis
        span = beam.span
        x0, x1 = x_map(0.0), x_map(span)
        self.canvas.create_line(x0, beam_y, x1, beam_y, fill=BLUE, width=9, capstyle="round")
        if beam.support == "Cantilever":
            self._draw_fixed_support(x0, beam_y)
            self.canvas.create_line(x1, beam_y - 10, x1, beam_y + 12, fill="#94a3b8", width=2)
        else:
            self._draw_simple_support(x0, beam_y, False)
            self._draw_simple_support(x1, beam_y, True)

        self._point_markers = []
        for load in beam.uniform_loads:
            if load.magnitude == 0.0 or load.start == load.end:
                continue
            start_x, end_x = x_map(load.start), x_map(load.end)
            load_scale = sqrt(load.magnitude / 10.0)
            arrow_length = 12.0 + 24.0 * load_scale
            arrow_scale = 0.75 + 0.75 * load_scale
            count = max(2, int((end_x - start_x) / 24))
            for index in range(count + 1):
                arrow_x = start_x + (end_x - start_x) * index / count
                self._arrow(
                    arrow_x,
                    beam_y - 7 - arrow_length,
                    beam_y - 7,
                    "#56657a",
                    arrow_scale,
                )
            self.canvas.create_text(
                (start_x + end_x) / 2,
                beam_y - 17 - arrow_length,
                text=f"{load.magnitude:g} k/ft",
                fill=INK, font=("Segoe UI", 9, "bold"),
            )
        for index, load in enumerate(beam.point_loads):
            if load.magnitude == 0.0:
                continue
            px = x_map(load.position)
            self._arrow(px, beam_y - 38, beam_y - 7, "#db4b4b")
            self.canvas.create_oval(px - 8, beam_y - 9, px + 8, beam_y + 7, fill="white", outline=BLUE, width=2)
            self.canvas.create_text(px, beam_y - 47, text=f"{load.magnitude:g} k", fill=INK, font=("Segoe UI", 9, "bold"))
            self._point_markers.append((px, index))

        self._draw_reactions(analysis, x_map, beam_y)
        self.canvas.create_text((x0 + x1) / 2, beam_y + 27, text=f"{span:g} ft span", fill=MUTED, font=("Segoe UI", 9))
        self._draw_deflected_beam(analysis, x_map, beam_y)

        shear_y0, shear_y1 = 150.0, 250.0
        moment_y0, moment_y1 = 263.0, 369.0
        deflection_y0, deflection_y1 = 394.0, min(height - 25.0, 505.0)
        self._draw_diagram(
            "SHEAR V (kips)", analysis, x_map, shear_y0, shear_y1,
            "shear", analysis.max_shear_x, analysis.max_shear,
        )
        self._draw_diagram(
            "MOMENT M (kip-ft)", analysis, x_map, moment_y0, moment_y1,
            "moment", analysis.max_moment_x, analysis.max_moment,
        )
        self._draw_diagram(
            "DEFLECTION y (in)", analysis, x_map, deflection_y0, deflection_y1,
            "deflection", analysis.max_deflection_x, analysis.max_deflection,
        )
        if self._hover_x is not None:
            hover_x = min(span, max(0.0, self._hover_x))
            px = x_map(hover_x)
            self.canvas.create_line(px, shear_y0, px, deflection_y1, fill="#4b5563", dash=(4, 3), width=1.2)
            values = (
                f"x {hover_x:.2f} ft   V {shear_at(beam, hover_x):.2f} k"
                f"   M {moment_at(beam, hover_x):.2f} kip-ft"
                f"   y {deflection_at(beam, hover_x):.3f} in"
            )
            self.canvas.create_text(width - 13, height - 8, text=values, anchor="se", fill=INK, font=("Segoe UI", 9, "bold"))

    def _draw_title(self, text: str, x: float, y: float) -> None:
        self.canvas.create_text(x, y, text=text, anchor="w", fill=MUTED, font=("Segoe UI", 9, "bold"))

    def _draw_placeholder(self, left: float, right: float, beam_y: float, height: float) -> None:
        self.canvas.create_line(left, beam_y, right, beam_y, fill=BLUE, width=9, capstyle="round")
        self.canvas.create_text(
            (left + right) / 2, height / 2, text="Enter valid beam and load values to show results.",
            fill=MUTED, font=("Segoe UI", 11),
        )

    def _beam_x_bounds(self, span: float, canvas_width: float | None = None) -> tuple[float, float]:
        width = canvas_width if canvas_width is not None else max(self.canvas.winfo_width(), 480)
        available_left, available_right = 76.0, width - 32.0
        visual_width = (available_right - available_left) * span / 40.0
        center = (available_left + available_right) / 2.0
        return center - visual_width / 2.0, center + visual_width / 2.0

    def _draw_simple_support(self, x: float, y: float, roller: bool) -> None:
        self.canvas.create_polygon(x, y + 3, x - 13, y + 20, x + 13, y + 20, fill="#dbeafe", outline=BLUE, width=2)
        self.canvas.create_line(x - 19, y + 21, x + 19, y + 21, fill="#64748b", width=2)
        if roller:
            self.canvas.create_oval(x - 7, y + 22, x - 1, y + 28, fill="white", outline="#64748b")
            self.canvas.create_oval(x + 1, y + 22, x + 7, y + 28, fill="white", outline="#64748b")

    def _draw_fixed_support(self, x: float, y: float) -> None:
        self.canvas.create_rectangle(x - 11, y - 10, x, y + 23, fill="#dbeafe", outline=BLUE, width=2)
        for offset in range(-8, 23, 8):
            self.canvas.create_line(x - 18, y + offset + 8, x - 11, y + offset, fill="#64748b", width=1)

    def _draw_reactions(self, result: Analysis, x_map: Any, beam_y: float) -> None:
        reactions = result.reactions
        x = x_map(0.0)
        self._arrow(x - 20, beam_y + 58, beam_y + 27, GREEN)
        self.canvas.create_text(x - 20, beam_y + 62, text=f"{reactions.left:.2f} k up", fill=GREEN, font=("Segoe UI", 8))
        if self._beam and self._beam.support == "Simply supported":
            x = x_map(self._beam.span)
            self._arrow(x + 18, beam_y + 58, beam_y + 27, GREEN)
            self.canvas.create_text(x + 18, beam_y + 62, text=f"{reactions.right:.2f} k up", fill=GREEN, font=("Segoe UI", 8))
        else:
            self.canvas.create_text(
                x_map(0.0) - 19, beam_y + 78, text=f"{reactions.fixed_moment:.2f} kip-ft CCW",
                fill=GREEN, font=("Segoe UI", 8), anchor="w",
            )

    def _draw_deflected_beam(self, result: Analysis, x_map: Any, beam_y: float) -> None:
        if not result.samples:
            return
        magnitude = max(result.max_deflection, 1e-8)
        scale = 23.0 / magnitude
        coords = []
        for sample in result.samples:
            coords.extend((x_map(sample.x), beam_y + 43 - sample.deflection * scale))
        if len(coords) >= 4:
            self.canvas.create_line(*coords, fill="#f59e0b", width=2, dash=(5, 3), smooth=True)
            self.canvas.create_text(
                x_map(self._beam.span if self._beam else 0.0), beam_y + 43,
                text="deflected (exaggerated)", anchor="ne", fill="#b77908", font=("Segoe UI", 8),
            )

    def _draw_diagram(
        self,
        title: str,
        result: Analysis,
        x_map: Any,
        top: float,
        bottom: float,
        kind: str,
        max_x: float,
        max_value: float,
    ) -> None:
        self._draw_title(title, 8, top - 8)
        x0, x1 = x_map(0.0), x_map(self._beam.span if self._beam else 20.0)
        zero_y = (top + bottom) / 2.0
        self.canvas.create_line(x0, zero_y, x1, zero_y, fill=LINE, width=1)
        if kind == "shear":
            points = list(result.shear_curve)
            values = [value for _, value in points]
        else:
            points = [
                (sample.x, getattr(sample, kind))
                for sample in result.samples
            ]
            values = [value for _, value in points]
        peak = max([abs(value) for value in values] + [1e-6])
        extent = (bottom - top) * 0.42
        coords: list[float] = []
        polygon: list[float] = [x0, zero_y]
        for x, value in points:
            py = zero_y - value / peak * extent
            px = x_map(x)
            coords.extend((px, py))
            polygon.extend((px, py))
        polygon.extend((x1, zero_y))
        color = {"shear": "#60a5fa", "moment": "#818cf8", "deflection": "#fbbf24"}[kind]
        if len(coords) >= 4:
            self.canvas.create_polygon(*polygon, fill=color, stipple="gray25", outline="")
            self.canvas.create_line(*coords, fill=BLUE_DARK if kind != "deflection" else "#d18b00", width=2)
        marker_value = self._value_at_x(result, kind, max_x)
        if kind == "shear":
            max_x, marker_value = max(result.shear_curve, key=lambda item: abs(item[1]))
        px = x_map(max_x)
        py = zero_y - (marker_value / peak) * extent
        self.canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill=RED, outline="white")
        unit = "k" if kind == "shear" else "kip-ft" if kind == "moment" else "in"
        self.canvas.create_text(
            x1 - 4, top - 8,
            text=f"{max_value:.3f} {unit} @ {max_x:.2f} ft",
            anchor="e",
            fill=INK, font=("Segoe UI", 8, "bold"),
            tags=("max-value",),
        )

    def _value_at_x(self, result: Analysis, kind: str, x: float) -> float:
        if kind == "shear" and self._beam:
            return shear_at(self._beam, x)
        if kind == "moment" and self._beam:
            return moment_at(self._beam, x)
        if self._beam:
            return deflection_at(self._beam, x)
        return 0.0

    def _arrow(self, x: float, y1: float, y2: float, color: str, scale: float = 1.0) -> None:
        self.canvas.create_line(
            x, y1, x, y2, fill=color, width=1.5 * scale, arrow="last",
            arrowshape=(7 * scale, 8 * scale, 3 * scale),
        )

    def _on_canvas_motion(self, event: tk.Event[Any]) -> None:
        if self._beam is None or event.y < 120 or event.y > 515:
            if self._hover_x is not None:
                self._hover_x = None
                self._draw()
            return
        left, right = self._beam_x_bounds(self._beam.span)
        self._hover_x = min(
            self._beam.span,
            max(0.0, (event.x - left) / max(1.0, right - left) * self._beam.span),
        )
        self._draw()

    def _on_canvas_leave(self, _event: tk.Event[Any]) -> None:
        if self._hover_x is not None:
            self._hover_x = None
            self._draw()

    def _on_canvas_press(self, event: tk.Event[Any]) -> None:
        if self._beam is None:
            return
        closest = min(self._point_markers, key=lambda item: abs(item[0] - event.x), default=None)
        if closest and abs(closest[0] - event.x) <= 12 and event.y < 110:
            self._dragging_point = closest[1]

    def _on_canvas_drag(self, event: tk.Event[Any]) -> None:
        if self._dragging_point is None or self._beam is None:
            return
        left, right = self._beam_x_bounds(self._beam.span)
        x = (event.x - left) / max(1.0, right - left) * self._beam.span
        snapped = min(self._beam.span, max(0.0, round(x * 4.0) / 4.0))
        if self._dragging_point < len(self._point_rows):
            self._point_rows[self._dragging_point]["position"].set(self._fmt(snapped))

    def _on_canvas_release(self, _event: tk.Event[Any]) -> None:
        self._dragging_point = None
        self._refresh_baseline()

    def _show_tooltip(self, text: str) -> None:
        self._hide_tooltip()
        self._tooltip = tk.Toplevel(self.root)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{self.root.winfo_pointerx() + 12}+{self.root.winfo_pointery() + 12}")
        tk.Label(
            self._tooltip, text=text, background="#172033", foreground="white",
            padx=8, pady=6, font=("Segoe UI", 9),
        ).pack()

    def _hide_tooltip(self) -> None:
        tooltip = getattr(self, "_tooltip", None)
        if tooltip is not None:
            tooltip.destroy()
            self._tooltip = None

    def _current_span_or_default(self) -> float:
        try:
            span = float(self.span_var.get())
            return span if 4.0 <= span <= 40.0 else 20.0
        except ValueError:
            return 20.0

    @staticmethod
    def _fmt(value: float) -> str:
        return f"{value:.4f}".rstrip("0").rstrip(".") if value % 1 else f"{value:.0f}"
