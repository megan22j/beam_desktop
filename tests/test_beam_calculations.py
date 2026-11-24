import unittest
import tempfile
import csv
from pathlib import Path

from beam_calculations import (
    BeamInput,
    PointLoad,
    UniformLoad,
    analyze_beam,
    deflection_at,
    scale_load_positions,
    shear_at,
)
from beam_persistence import beam_from_dict, beam_to_dict, open_beam, save_beam
from beam_export import analysis_to_csv
from beam_pdf import analysis_to_pdf


class BeamCalculationTests(unittest.TestCase):
    def test_simply_supported_full_span_uniform_load(self):
        result = analyze_beam(BeamInput())
        self.assertAlmostEqual(result.reactions.left, 10.0, places=8)
        self.assertAlmostEqual(result.reactions.right, 10.0, places=8)
        self.assertAlmostEqual(result.max_shear, 10.0, places=8)
        self.assertAlmostEqual(result.max_moment, 50.0, places=8)
        self.assertAlmostEqual(result.max_moment_x, 10.0, places=8)
        self.assertAlmostEqual(result.bending_stress, 17.96, places=2)
        self.assertAlmostEqual(result.max_deflection, 0.609, places=3)
        self.assertAlmostEqual(result.max_deflection_x, 10.0, places=8)
        self.assertTrue(result.bending_pass)
        self.assertTrue(result.deflection_pass)

    def test_simply_supported_point_load_between_supports(self):
        beam = BeamInput(
            point_loads=(PointLoad(10.0, 5.0),),
            uniform_loads=(),
        )
        result = analyze_beam(beam)
        self.assertAlmostEqual(result.reactions.left, 7.5, places=8)
        self.assertAlmostEqual(result.reactions.right, 2.5, places=8)
        self.assertAlmostEqual(result.max_moment, 37.5, places=8)
        self.assertAlmostEqual(result.max_moment_x, 5.0, places=8)
        self.assertAlmostEqual(result.bending_stress, 13.47, places=2)
        self.assertAlmostEqual(result.max_deflection, 0.340, places=3)
        self.assertAlmostEqual(result.max_deflection_x, 8.82, places=2)

    def test_cantilever_free_end_point_load(self):
        beam = BeamInput(
            span=10.0,
            support="Cantilever",
            point_loads=(PointLoad(5.0, 10.0),),
            uniform_loads=(),
        )
        result = analyze_beam(beam)
        self.assertAlmostEqual(result.reactions.left, 5.0, places=8)
        self.assertAlmostEqual(result.reactions.fixed_moment, 50.0, places=8)
        self.assertAlmostEqual(result.max_moment, 50.0, places=8)
        self.assertAlmostEqual(result.max_deflection, 0.487, places=3)
        self.assertAlmostEqual(result.max_deflection_x, 10.0, places=8)
        self.assertTrue(result.bending_pass)
        self.assertFalse(result.deflection_pass)

    def test_lumber_uniform_load(self):
        beam = BeamInput(
            span=12.0,
            uniform_loads=(UniformLoad(0.05, 0.0, 12.0),),
            material="Lumber",
            section="2x10",
        )
        result = analyze_beam(beam)
        self.assertAlmostEqual(result.max_moment, 0.9, places=8)
        self.assertAlmostEqual(result.bending_stress, 0.505, places=3)
        self.assertAlmostEqual(result.max_deflection, 0.147, places=3)
        self.assertTrue(result.bending_pass)
        self.assertTrue(result.deflection_pass)

    def test_partial_uniform_load(self):
        beam = BeamInput(
            span=30.0,
            uniform_loads=(UniformLoad(2.0, 0.0, 15.0),),
            section="W18x35",
        )
        result = analyze_beam(beam)
        self.assertAlmostEqual(result.reactions.left, 22.5, places=8)
        self.assertAlmostEqual(result.reactions.right, 7.5, places=8)
        self.assertAlmostEqual(result.max_moment, 126.5625, places=7)
        self.assertAlmostEqual(result.max_moment_x, 11.25, places=8)

    def test_point_load_shear_has_a_jump_at_its_position(self):
        beam = BeamInput(
            span=10.0,
            point_loads=(PointLoad(2.0, 4.0),),
            uniform_loads=(),
        )
        self.assertAlmostEqual(
            shear_at(beam, 4.0, "right") - shear_at(beam, 4.0, "left"),
            -2.0,
        )

    def test_uniform_load_with_equal_bounds_has_no_effect(self):
        empty = BeamInput(uniform_loads=())
        zero_length = BeamInput(uniform_loads=(UniformLoad(3.0, 7.0, 7.0),))
        self.assertAlmostEqual(
            analyze_beam(empty).max_moment,
            analyze_beam(zero_length).max_moment,
        )
        self.assertAlmostEqual(deflection_at(zero_length, 10.0), deflection_at(empty, 10.0))

    def test_span_scaling_preserves_relative_load_positions(self):
        points, uniforms = scale_load_positions(
            (PointLoad(2.0, 5.0),),
            (UniformLoad(1.0, 2.0, 8.0),),
            10.0,
            20.0,
        )
        self.assertEqual(points, (PointLoad(2.0, 10.0),))
        self.assertEqual(uniforms, (UniformLoad(1.0, 4.0, 16.0),))

    def test_saved_beam_round_trips_complete_state(self):
        beam = BeamInput(
            span=18.5,
            support="Cantilever",
            point_loads=(PointLoad(7.25, 18.5),),
            uniform_loads=(UniformLoad(2.5, 3.0, 14.0),),
            material="Lumber",
            section="2x12",
            deflection_limit=240,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cantilever.beam.json"
            save_beam(path, beam)
            loaded = open_beam(path)

        self.assertEqual(loaded, beam)
        self.assertEqual(beam_from_dict(beam_to_dict(beam)), beam)

    def test_invalid_saved_file_format_is_rejected(self):
        data = {"format": "Another App", "version": 1}
        with self.assertRaisesRegex(ValueError, "not a Beam Designer file"):
            beam_from_dict(data)

    def test_results_export_to_csv(self):
        analysis = analyze_beam(BeamInput())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "beam-results.csv"
            analysis_to_csv(path, analysis)
            with path.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows[0],
            ["x_ft", "V_kips", "M_kip_ft", "deflection_in"],
        )
        self.assertGreater(len(rows), 40)
        self.assertEqual(len(rows[1]), 4)
        self.assertEqual(float(rows[1][0]), 0.0)

    def test_calculation_sheet_exports_pdf(self):
        beam = BeamInput()
        analysis = analyze_beam(beam)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "beam-calculation.pdf"
            analysis_to_pdf(path, beam, analysis)
            header = path.read_bytes()[:8]
            size = path.stat().st_size

        self.assertTrue(header.startswith(b"%PDF-"))
        self.assertGreater(size, 1000)

    def test_invalid_load_bounds_are_rejected(self):
        beam = BeamInput(uniform_loads=(UniformLoad(1.0, 8.0, 7.0),))
        with self.assertRaisesRegex(ValueError, "start must not be after"):
            analyze_beam(beam)

    def test_section_recommendation_and_no_passing_result(self):
        self.assertEqual(analyze_beam(BeamInput()).recommendation.name, "W14x22")
        overloaded = BeamInput(
            span=40.0,
            uniform_loads=(UniformLoad(10.0, 0.0, 40.0),),
        )
        self.assertIsNone(analyze_beam(overloaded).recommendation)


if __name__ == "__main__":
    unittest.main()
