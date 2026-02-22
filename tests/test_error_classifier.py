"""
Unit tests for the SDC4 ErrorClassifier.

Adapted from vaas test_error_mapper.py — replaces ExceptionalValueType
assertions with ErrorTier assertions.
"""

import unittest
from xmlschema.validators.exceptions import (
    XMLSchemaValidationError,
    XMLSchemaDecodeError,
    XMLSchemaChildrenValidationError
)
from sdcvalidator.error_classifier import ErrorClassifier
from sdcvalidator.constants import ErrorTier


class TestErrorClassifier(unittest.TestCase):
    """Test cases for the ErrorClassifier class."""

    def setUp(self):
        self.classifier = ErrorClassifier()

    def test_type_violation_is_semantic(self):
        """Type violations are semantic (Tier 2)."""
        error = XMLSchemaValidationError(
            validator=None,
            obj="invalid_value",
            reason="not a valid value for type xs:integer"
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)

    def test_enumeration_violation_is_semantic(self):
        """Enumeration violations are semantic (Tier 2)."""
        error = XMLSchemaValidationError(
            validator=None,
            obj="bad_value",
            reason="value not in enumeration ['option1', 'option2']"
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)

    def test_missing_required_is_semantic(self):
        """Missing required elements are semantic (Tier 2) unless children error."""
        error = XMLSchemaValidationError(
            validator=None,
            obj=None,
            reason="missing required element 'field_name'"
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)

    def test_pattern_violation_is_semantic(self):
        """Pattern violations are semantic (Tier 2)."""
        error = XMLSchemaValidationError(
            validator=None,
            obj="abc123",
            reason="does not match pattern '[0-9]+'"
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)

    def test_decode_error_is_semantic(self):
        """Decode errors are semantic (Tier 2)."""
        error = XMLSchemaDecodeError(
            validator=None,
            obj="not_a_number",
            decoder=None,
            reason="cannot be converted to integer"
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)

    def test_unknown_element_is_structural(self):
        """Unknown elements (ChildrenValidationError with invalid_tag) are structural."""
        class MockChildrenError(XMLSchemaChildrenValidationError):
            def __init__(self):
                self.invalid_tag = '{http://example.com}UnknownTag'
                self._reason = "Unexpected child with tag 'UnknownTag'"
                self._path = '/root/UnknownTag'

            @property
            def reason(self):
                return self._reason

            @property
            def path(self):
                return self._path

        error = MockChildrenError()
        self.assertEqual(self.classifier.classify(error), ErrorTier.STRUCTURAL)

    def test_cardinality_violation_is_structural(self):
        """Cardinality violations are structural (Tier 1)."""
        class MockCardinalityError(XMLSchemaChildrenValidationError):
            def __init__(self):
                self.invalid_tag = None
                self._reason = "The particle 'element' occurs 0 times but the minimum is 1"
                self._path = '/root/element'

            @property
            def reason(self):
                return self._reason

            @property
            def path(self):
                return self._path

        error = MockCardinalityError()
        self.assertEqual(self.classifier.classify(error), ErrorTier.STRUCTURAL)

    def test_default_fallback_is_semantic(self):
        """Unknown errors with no reason fall back to semantic."""
        error = XMLSchemaValidationError(
            validator=None,
            obj="something",
            reason=None
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)

    def test_classify_all_separates_errors(self):
        """classify_all correctly buckets errors."""
        semantic_error = XMLSchemaValidationError(
            validator=None,
            obj="bad",
            reason="not a valid value"
        )

        class MockStructuralError(XMLSchemaChildrenValidationError):
            def __init__(self):
                self.invalid_tag = '{http://example.com}Bad'
                self._reason = "Unexpected child"
                self._path = '/root/Bad'

            @property
            def reason(self):
                return self._reason

            @property
            def path(self):
                return self._path

        structural_error = MockStructuralError()

        result = self.classifier.classify_all([semantic_error, structural_error])

        self.assertEqual(len(result["structural"]), 1)
        self.assertEqual(len(result["semantic"]), 1)

    def test_error_summary(self):
        """Error summaries include tier classification."""
        error = XMLSchemaValidationError(
            validator=None,
            obj="invalid_value",
            reason="not a valid value for type xs:integer"
        )
        error._path = "/root/element[1]"

        summary = self.classifier.get_error_summary(error)

        self.assertEqual(summary['tier'], 'semantic')
        self.assertEqual(summary['xpath'], '/root/element[1]')
        self.assertIn('not a valid value', summary['reason'])

    def test_constraint_violation_is_semantic(self):
        """Constraint violations (maxLength etc.) are semantic."""
        error = XMLSchemaValidationError(
            validator=None,
            obj="toolongstring",
            reason="length constraint violated: maxLength is 10"
        )
        self.assertEqual(self.classifier.classify(error), ErrorTier.SEMANTIC)


if __name__ == '__main__':
    unittest.main()
