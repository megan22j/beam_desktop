# Beam Designer (Tkinter)

A resizable Python desktop app for checking simply supported beams and
cantilevers with point and uniform loads. The existing browser prototype in
`index.html` is preserved.

The beam drawing uses a consistent horizontal scale based on the 40 ft
maximum span, so changing the span visibly changes the beam and aligned
diagrams.

Uniform-load arrows scale in length and arrowhead size with the load's kips
per foot.

Use **File > Save** or Ctrl+S to save the complete beam setup as JSON.
Use **File > Open** or Ctrl+O to restore a saved setup.

Use **Export Results** to save x, shear, moment, and deflection values as a
CSV. On Windows, the CSV opens in the associated spreadsheet application.

Use **Calculation Sheet** to save a submission-ready PDF with the inputs,
beam drawing, three diagrams, reactions, section, and design checks.

## Run

Use Python 3.10 or newer with Tkinter available:

```powershell
python main.py
```

The app uses only the Python standard library. It opens with a 20 ft simply
supported W12x26 beam under a 1 kip/ft uniform load.

## Test

```powershell
python -m unittest discover -s tests -v
```

The calculation tests cover the five numerical examples in `spec.md`, as well
as load endpoints, span scaling, and invalid uniform-load bounds. Beam
calculations are independent of Tkinter and can be tested without opening a
window.
