#
# Copyright (c), 2025, Axius-SDC, Inc.
# All rights reserved.
# This file is distributed under the terms of the MIT License.
#
"""
Tests for SDC4 schema compliance validation.

Tests the validation that XSD schemas follow SDC4 principles:
- No xsd:extension elements (only xsd:restriction allowed)
- Enforces separation of structure and semantics
"""

import pytest
from pathlib import Path

from sdcvalidator.sdc4 import (
    validate_sdc4_schema_compliance,
    assert_sdc4_schema_compliance,
    SDC4SchemaValidationError,
    SDC4Validator
)


# Get test schemas directory
TEST_SCHEMAS_DIR = Path(__file__).parent / 'test_schemas'
VALID_SCHEMA = TEST_SCHEMAS_DIR / 'valid_sdc4_schema.xsd'
INVALID_SCHEMA = TEST_SCHEMAS_DIR / 'invalid_sdc4_schema_with_extension.xsd'
NON_SDC4_SCHEMA = TEST_SCHEMAS_DIR / 'non_sdc4_schema_with_extension.xsd'


class TestValidateSDC4SchemaCompliance:
    """Tests for validate_sdc4_schema_compliance() function."""

    def test_valid_schema_passes(self):
        """Test that a valid SDC4 schema (using only restriction) passes validation."""
        is_valid, errors = validate_sdc4_schema_compliance(VALID_SCHEMA)

        assert is_valid is True
        assert errors == []

    def test_invalid_schema_with_extension_fails(self):
        """Test that a schema with xsd:extension fails validation."""
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)

        assert is_valid is False
        assert len(errors) > 0

        # Check that error message contains expected details
        error_msg = errors[0]
        assert 'xsd:extension' in error_msg
        assert 'PatientNameExtended' in error_msg
        assert 'XdStringType' in error_msg
        assert 'xsd:restriction' in error_msg

    def test_nonexistent_file_returns_error(self):
        """Test that attempting to validate non-existent file returns error."""
        is_valid, errors = validate_sdc4_schema_compliance('/path/to/nonexistent.xsd')

        assert is_valid is False
        assert len(errors) == 1
        assert 'not found' in errors[0].lower()

    def test_invalid_xml_returns_error(self):
        """Test that invalid XML returns parse error."""
        # Create a temporary invalid XML file
        import tempfile
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
        """Test that non-SDC4 schemas with xsd:extension pass validation."""
        is_valid, errors = validate_sdc4_schema_compliance(NON_SDC4_SCHEMA)

        assert is_valid is True
        assert errors == []


class TestAssertSDC4SchemaCompliance:
    """Tests for assert_sdc4_schema_compliance() function."""

    def test_valid_schema_does_not_raise(self):
        """Test that valid schema does not raise exception."""
        # Should not raise any exception
        assert_sdc4_schema_compliance(VALID_SCHEMA)

    def test_invalid_schema_raises_exception(self):
        """Test that invalid schema raises SDC4SchemaValidationError."""
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            assert_sdc4_schema_compliance(INVALID_SCHEMA)

        error_msg = str(exc_info.value)
        assert 'violates SDC4 compliance' in error_msg
        assert 'xsd:extension' in error_msg
        assert 'PatientNameExtended' in error_msg

    def test_nonexistent_file_raises_exception(self):
        """Test that non-existent file raises SDC4SchemaValidationError."""
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            assert_sdc4_schema_compliance('/path/to/nonexistent.xsd')

        error_msg = str(exc_info.value)
        assert 'not found' in error_msg.lower()


class TestSDC4ValidatorIntegration:
    """Tests for SDC4Validator integration with schema compliance checking."""

    def test_validator_accepts_valid_schema(self):
        """Test that SDC4Validator accepts valid schema with compliance check enabled."""
        # Should not raise any exception
        validator = SDC4Validator(VALID_SCHEMA, check_sdc4_compliance=True)

        assert validator is not None
        assert validator.schema is not None

    def test_validator_rejects_invalid_schema(self):
        """Test that SDC4Validator rejects invalid schema with compliance check enabled."""
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            SDC4Validator(INVALID_SCHEMA, check_sdc4_compliance=True)

        error_msg = str(exc_info.value)
        assert 'violates SDC4 compliance' in error_msg
        assert 'xsd:extension' in error_msg

    def test_validator_bypass_compliance_check(self):
        """Test that SDC4Validator can bypass compliance check when disabled."""
        # Should not raise exception even with invalid schema
        validator = SDC4Validator(INVALID_SCHEMA, check_sdc4_compliance=False)

        assert validator is not None
        assert validator.schema is not None

    def test_validator_compliance_check_default_enabled(self):
        """Test that compliance check is enabled by default."""
        # Should raise exception with invalid schema (default behavior)
        with pytest.raises(SDC4SchemaValidationError):
            SDC4Validator(INVALID_SCHEMA)


class TestErrorMessageQuality:
    """Tests for quality and usefulness of error messages."""

    def test_error_message_includes_type_name(self):
        """Test that error messages include the type name using extension."""
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)

        assert not is_valid
        assert any('PatientNameExtended' in error for error in errors)

    def test_error_message_includes_base_type(self):
        """Test that error messages include the base type being extended."""
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)

        assert not is_valid
        assert any('XdStringType' in error for error in errors)

    def test_error_message_includes_sdc4_principle(self):
        """Test that error messages explain SDC4 principle."""
        is_valid, errors = validate_sdc4_schema_compliance(INVALID_SCHEMA)

        assert not is_valid
        assert any('xsd:restriction' in error for error in errors)
        assert any('separation' in error.lower() for error in errors)
        assert any('global interoperability' in error.lower() for error in errors)

    def test_exception_message_formatting(self):
        """Test that raised exception has well-formatted message."""
        with pytest.raises(SDC4SchemaValidationError) as exc_info:
            assert_sdc4_schema_compliance(INVALID_SCHEMA)

        error_msg = str(exc_info.value)

        # Should have structured formatting
        assert '❌' in error_msg  # Emoji for visual clarity
        assert 'SDC4 Principle:' in error_msg  # Educational content
        assert 'separation of structure and semantics' in error_msg
        assert 'global interoperability' in error_msg.lower()
