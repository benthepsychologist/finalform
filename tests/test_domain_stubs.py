"""Tests for domain processor stubs."""

import pytest

from final_form.core import DomainProcessor
from final_form.domains import LabProcessor, VitalProcessor, WearableProcessor


class TestLabProcessor:
    """Tests for LabProcessor stub."""

    def test_implements_protocol(self) -> None:
        """Test that LabProcessor implements DomainProcessor protocol."""
        processor = LabProcessor()
        assert isinstance(processor, DomainProcessor)

    def test_supported_kinds(self) -> None:
        """Test supported kinds."""
        processor = LabProcessor()
        assert processor.supported_kinds == ("lab_panel",)

    def test_process_raises_not_implemented(self) -> None:
        """Test that process raises NotImplementedError."""
        processor = LabProcessor()
        with pytest.raises(NotImplementedError):
            processor.process({}, None, {})  # type: ignore

    def test_validate_raises_not_implemented(self) -> None:
        """Test that validate_measure raises NotImplementedError."""
        processor = LabProcessor()
        with pytest.raises(NotImplementedError):
            processor.validate_measure(None)  # type: ignore


class TestVitalProcessor:
    """Tests for VitalProcessor stub."""

    def test_implements_protocol(self) -> None:
        """Test that VitalProcessor implements DomainProcessor protocol."""
        processor = VitalProcessor()
        assert isinstance(processor, DomainProcessor)

    def test_supported_kinds(self) -> None:
        """Test supported kinds."""
        processor = VitalProcessor()
        assert processor.supported_kinds == ("vital",)

    def test_process_raises_not_implemented(self) -> None:
        """Test that process raises NotImplementedError."""
        processor = VitalProcessor()
        with pytest.raises(NotImplementedError):
            processor.process({}, None, {})  # type: ignore

    def test_validate_raises_not_implemented(self) -> None:
        """Test that validate_measure raises NotImplementedError."""
        processor = VitalProcessor()
        with pytest.raises(NotImplementedError):
            processor.validate_measure(None)  # type: ignore


class TestWearableProcessor:
    """Tests for WearableProcessor stub."""

    def test_implements_protocol(self) -> None:
        """Test that WearableProcessor implements DomainProcessor protocol."""
        processor = WearableProcessor()
        assert isinstance(processor, DomainProcessor)

    def test_supported_kinds(self) -> None:
        """Test supported kinds."""
        processor = WearableProcessor()
        assert processor.supported_kinds == ("wearable",)

    def test_process_raises_not_implemented(self) -> None:
        """Test that process raises NotImplementedError."""
        processor = WearableProcessor()
        with pytest.raises(NotImplementedError):
            processor.process({}, None, {})  # type: ignore

    def test_validate_raises_not_implemented(self) -> None:
        """Test that validate_measure raises NotImplementedError."""
        processor = WearableProcessor()
        with pytest.raises(NotImplementedError):
            processor.validate_measure(None)  # type: ignore
