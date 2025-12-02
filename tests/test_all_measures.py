"""Tests for all measures in the registry.

Ensures all measure specs can be loaded and validated,
and that the scoring engine can process them.
"""

from pathlib import Path

import pytest

from final_form.registry import MeasureRegistry


@pytest.fixture
def measure_registry(measure_registry_path: Path, measure_schema_path: Path) -> MeasureRegistry:
    """Create measure registry with schema validation."""
    return MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)


class TestAllMeasures:
    """Tests that verify all measures load and have valid structure."""

    def test_list_all_measures(self, measure_registry: MeasureRegistry) -> None:
        """Test listing all available measures."""
        measures = measure_registry.list_measures()

        # Should have at least our converted measures
        expected = {
            "phq9", "gad7",  # Original
            "msi", "safe", "phlms_10", "joy",  # Converted
            "sleep_disturbances", "trauma_exposure", "ptsd_screen",
            "ipip_neo_60_c", "fscrs", "pss_10",
        }

        for measure_id in expected:
            assert measure_id in measures, f"Missing measure: {measure_id}"

    def test_load_all_measures(self, measure_registry: MeasureRegistry) -> None:
        """Test that all measures can be loaded."""
        measures = measure_registry.list_measures()

        for measure_id in measures:
            spec = measure_registry.get_latest(measure_id)
            assert spec is not None
            assert spec.measure_id == measure_id
            assert len(spec.items) > 0
            assert len(spec.scales) > 0

    def test_phq9_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test PHQ-9 measure structure."""
        spec = measure_registry.get("phq9", "1.0.0")

        assert spec.name == "Patient Health Questionnaire-9"
        assert spec.kind == "questionnaire"
        assert len(spec.items) == 10  # 9 symptom + 1 severity
        assert len(spec.scales) == 2  # total + severity

    def test_gad7_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test GAD-7 measure structure."""
        spec = measure_registry.get("gad7", "1.0.0")

        assert spec.name == "Generalized Anxiety Disorder-7"
        assert len(spec.items) == 8  # 7 symptom + 1 severity
        assert len(spec.scales) == 2

    def test_pss10_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test PSS-10 measure structure."""
        spec = measure_registry.get("pss_10", "1.0.0")

        assert spec.name == "Perceived Stress Scale (10-item)"
        assert len(spec.items) == 10

        # Check for reversed items in scale
        scale = spec.get_scale("pss_10")
        assert scale is not None
        assert len(scale.reversed_items) == 4  # Items 4, 5, 7, 8

    def test_fscrs_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test FSCRS measure structure."""
        spec = measure_registry.get("fscrs", "1.0.0")

        assert "Self-Criticizing" in spec.name
        assert len(spec.items) == 22

        # Should have multiple scales
        assert len(spec.scales) >= 3  # inadequacy, self_hatred, self_reassurance

    def test_ipip_neo_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test IPIP-NEO-60 Conscientiousness structure."""
        spec = measure_registry.get("ipip_neo_60_c", "1.0.0")

        assert "Conscientiousness" in spec.name
        assert len(spec.items) == 12

        # Should have composite and facet scales
        assert len(spec.scales) >= 7  # 1 composite + 6 facets

    def test_phlms10_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test PHLMS-10 mindfulness structure."""
        spec = measure_registry.get("phlms_10", "1.0.0")

        assert "Philadelphia Mindfulness" in spec.name
        assert len(spec.items) == 10

        # Should have awareness and acceptance subscales
        att_scale = spec.get_scale("phlms_att")
        acc_scale = spec.get_scale("phlms_acc")
        assert att_scale is not None
        assert acc_scale is not None

        # sum_then_double method
        assert att_scale.method == "sum_then_double"
        assert acc_scale.method == "sum_then_double"

    def test_trauma_exposure_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test trauma exposure screener structure."""
        spec = measure_registry.get("trauma_exposure", "1.0.0")

        assert len(spec.items) == 17  # Life events checklist items

    def test_ptsd_screen_structure(self, measure_registry: MeasureRegistry) -> None:
        """Test PTSD screener structure."""
        spec = measure_registry.get("ptsd_screen", "1.0.0")

        assert len(spec.items) == 5  # PC-PTSD-5 style

    def test_all_measures_have_interpretations(self, measure_registry: MeasureRegistry) -> None:
        """Test that all scales have interpretations."""
        measures = measure_registry.list_measures()

        for measure_id in measures:
            spec = measure_registry.get_latest(measure_id)

            for scale in spec.scales:
                assert len(scale.interpretations) > 0, \
                    f"Scale {scale.scale_id} in {measure_id} has no interpretations"

    def test_all_response_maps_have_values(self, measure_registry: MeasureRegistry) -> None:
        """Test that all items have non-empty response maps."""
        measures = measure_registry.list_measures()

        for measure_id in measures:
            spec = measure_registry.get_latest(measure_id)

            for item in spec.items:
                assert len(item.response_map) > 0, \
                    f"Item {item.item_id} in {measure_id} has no response map"
