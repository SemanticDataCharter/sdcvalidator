"""
Tests for SDC4 schema compliance validation.

Adapted from vaas test_schema_validator.py — updated imports only.
"""

import pytest
import tempfile
from pathlib import Path

from sdcvalidator import (
    validate_sdc4_schema_compliance,
    assert_sdc4_schema_compliance,
    SDC4SchemaValidationError,
    SDC4Validator,
)


TEST_SCHEMAS_DIR = Path(__file__).parent / 'test_data'
VALID_SCHEMA = TEST_SCHEMAS_DIR / 'valid_sdc4_schema.xsd'
INVALID_SCHEMA = TEST_SCHEMAS_DIR / 'invalid_sdc4_schema_with_extension.xsd'
NON_SDC4_SCHEMA = TEST_SCHEMAS_DIR / 'non_sdc4_schema_with_extension.xsd'


class TestValidateSDC4SchemaCompliance:
    """Tests for validate_sdc4_schema_compliance() function."""

    def test_valid_schema_passes(self):
        is_valid, errors = validate_sdc4_schema_compliance(VALID_SCHEMA)
        assert is_valid is True
        assert errors == []

    def test_invalid_schema_with_extension_fails(self):
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)
        assert is_valid is False
        assert len(errors) > 0

        error_msg = errors[0]
        assert 'xsd:extension' in error_msg
        assert 'PatientNameExtended' in error_msg
        assert 'XdStringType' in error_msg
        assert 'xsd:restriction' in error_msg

    def test_nonexistent_file_returns_error(self):
        is_valid, errors = validate_sdc4_schema_compliance('/path/to/nonexistent.xsd')
        assert is_valid is False
        assert len(errors) == 1
        assert 'not found' in errors[0].lower()

    def test_invalid_xml_returns_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xsd', delete=False) as f:
            f.write('<?xml version="1.0"?><invalid><unclosed>')
            temp_path = f.name

        try:
            is_valid, errors = validate_sdc4_schema_compliance(temp_path)
            assert is_valid is False
            assert len(errors) == 1
            assert 'parse' in errors[0].lower()
        finally:
            Path(temp_path).unlink()

    def test_non_sdc4_schema_with_extension_passes(self):
        is_valid, errors = validate_sdc4_schema_compliance(NON_SDC4_SCHEMA)
        assert is_valid is True
        assert errors == []


class TestAssertSDC4SchemaCompliance:
    """Tests for assert_sdc4_schema_compliance() function."""

    def test_valid_schema_does_not_raise(self):
        assert_sdc4_schema_compliance(VALID_SCHEMA)

    def test_invalid_schema_raises_exception(self):
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            assert_sdc4_schema_compliance(INVALID_SCHEMA)

        error_msg = str(exc_info.value)
        assert 'violates SDC4 compliance' in error_msg
        assert 'xsd:extension' in error_msg
        assert 'PatientNameExtended' in error_msg

    def test_nonexistent_file_raises_exception(self):
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            assert_sdc4_schema_compliance('/path/to/nonexistent.xsd')

        error_msg = str(exc_info.value)
        assert 'not found' in error_msg.lower()


class TestSDC4ValidatorIntegration:
    """Tests for SDC4Validator integration with schema compliance checking."""

    def test_validator_accepts_valid_schema(self):
        validator = SDC4Validator(VALID_SCHEMA, check_sdc4_compliance=True)
        assert validator is not None
        assert validator.schema is not None

    def test_validator_rejects_invalid_schema(self):
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            SDC4Validator(INVALID_SCHEMA, check_sdc4_compliance=True)

        error_msg = str(exc_info.value)
        assert 'violates SDC4 compliance' in error_msg
        assert 'xsd:extension' in error_msg

    def test_validator_bypass_compliance_check(self):
        validator = SDC4Validator(INVALID_SCHEMA, check_sdc4_compliance=False)
        assert validator is not None
        assert validator.schema is not None

    def test_validator_compliance_check_default_enabled(self):
        with pytest.raises(SDC4SchemaValidationError):
            SDC4Validator(INVALID_SCHEMA)


class TestErrorMessageQuality:
    """Tests for quality and usefulness of error messages."""

    def test_error_message_includes_type_name(self):
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)
        assert not is_valid
        assert any('PatientNameExtended' in error for error in errors)

    def test_error_message_includes_base_type(self):
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)
        assert not is_valid
        assert any('XdStringType' in error for error in errors)

    def test_error_message_includes_sdc4_principle(self):
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)
        assert not is_valid
        assert any('xsd:restriction' in error for error in errors)
        assert any('separation' in error.lower() for error in errors)
        assert any('global interoperability' in error.lower() for error in errors)

    def test_exception_message_formatting(self):
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            assert_sdc4_schema_compliance(INVALID_SCHEMA)

        error_msg = str(exc_info.value)
        assert 'SDC4 Principle:' in error_msg
        assert 'separation of structure and semantics' in error_msg
        assert 'global interoperability' in error_msg.lower()
