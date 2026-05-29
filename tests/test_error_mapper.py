#
# Copyright 2025 Semantic Data Charter Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
"""
Unit tests for the SDC4 error mapper.
"""

import unittest
from xmlschema.validators.exceptions import (
    XMLSchemaValidationError,
    XMLSchemaDecodeError,
)
from sdcvalidator import ErrorMapper, ExceptionalValueType


class TestErrorMapper(unittest.TestCase):
    """Test cases for the ErrorMapper class."""

    def setUp(self):
        self.mapper = ErrorMapper()

    def test_type_violation_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="invalid_value",
            reason="not a valid value for type xs:integer"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.INV)

    def test_enumeration_violation_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="bad_value",
            reason="value not in enumeration ['option1', 'option2']"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.OTH)

    def test_missing_required_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj=None,
            reason="missing required element 'field_name'"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.NI)

    def test_pattern_violation_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="abc123",
            reason="does not match pattern '[0-9]+'"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.INV)

    def test_unexpected_content_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="unexpected_element",
            reason="unexpected element 'field' not allowed here"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.NA)

    def test_encoding_error_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="bad\x00char",
            reason="encoding error: invalid character in string"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.UNC)

    def test_decode_error_mapping(self):
        error = XMLSchemaDecodeError(
            validator=None,
            obj="not_a_number",
            decoder=None,
            reason="cannot be converted to integer"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.INV)

    def test_default_fallback_mapping(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="something",
            reason=None
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.NI)

    def test_custom_rule_addition(self):
        def is_masked_error(err):
            return err.reason and 'confidential' in err.reason.lower()

        error = XMLSchemaValidationError(
            validator=None,
            obj="secret_data",
            reason="This field contains confidential information"
        )

        mapper = ErrorMapper()
        mapper._rules.insert(0, (is_masked_error, ExceptionalValueType.MSK))
        self.assertEqual(mapper.map_error(error), ExceptionalValueType.MSK)

    def test_error_summary_generation(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="invalid_value",
            reason="not a valid value for type xs:integer"
        )
        error._path = "/root/element[1]"

        ev_type = self.mapper.map_error(error)
        summary = self.mapper.get_error_summary(error, ev_type)

        self.assertEqual(summary['exceptional_value_type'], 'INV')
        self.assertEqual(summary['exceptional_value_name'], 'Invalid')
        self.assertEqual(summary['xpath'], '/root/element[1]')
        self.assertIn('not a valid value', summary['reason'])

    def test_constraint_violation_max_length(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj="toolongstring",
            reason="length constraint violated: maxLength is 10"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.INV)

    def test_constraint_violation_min_inclusive(self):
        error = XMLSchemaValidationError(
            validator=None,
            obj=-5,
            reason="value -5 is below minimum inclusive of 0"
        )
        self.assertEqual(self.mapper.map_error(error), ExceptionalValueType.INV)

    def test_is_structural_error_delegates_to_classifier(self):
        """is_structural_error must agree with a standalone ErrorClassifier."""
        from sdcvalidator import ErrorClassifier
        clf = ErrorClassifier()
        error = XMLSchemaValidationError(
            validator=None, obj="x", reason="unexpected child element 'foo'"
        )
        self.assertEqual(
            self.mapper.is_structural_error(error),
            clf.is_structural_error(error),
        )


if __name__ == '__main__':
    unittest.main()
