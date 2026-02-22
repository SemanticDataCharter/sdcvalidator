"""
Tests for SDC4Validator — two-tier classification without EV injection.

Adapted from vaas test_two_tier.py — tests classify without recovery.
"""

import unittest
import tempfile
from pathlib import Path

from sdcvalidator.validator import SDC4Validator, ValidationResult
from sdcvalidator.error_classifier import ErrorClassifier
from sdcvalidator.constants import ErrorTier
from xmlschema.validators.exceptions import (
    XMLSchemaValidationError,
    XMLSchemaChildrenValidationError,
    XMLSchemaDecodeError,
)


class TestSDC4Validator(unittest.TestCase):
    """Tests for the SDC4Validator class."""

    def setUp(self):
        self.schema_path = Path(__file__).parent / 'test_data' / 'dm-jsi5yxnvzsmsisgn2bvelkni.xsd'
        if not self.schema_path.exists():
            self.skipTest(f"SDC4 example schema not found at {self.schema_path}")

    def test_structural_error_detected(self):
        """Unknown elements are classified as structural errors."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
    <MaliciousTag>attack_payload</MaliciousTag>
    <sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
        <label>StatePopulation Data Cluster</label>
    </sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            validator = SDC4Validator(self.schema_path)
            result = validator.validate(xml_path)

            self.assertFalse(result.is_valid)
            self.assertGreater(len(result.structural_errors), 0)
        finally:
            xml_path.unlink()

    def test_misspelled_element_is_structural(self):
        """Misspelled elements are structural errors."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-labl>StatePopulation</dm-labl>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            validator = SDC4Validator(self.schema_path)
            result = validator.validate(xml_path)

            self.assertFalse(result.is_valid)
            self.assertGreater(len(result.structural_errors), 0)
        finally:
            xml_path.unlink()

    def test_semantic_error_detected(self):
        """Type violations are classified as semantic errors."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
    <sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
        <label>StatePopulation Data Cluster</label>
        <sdc4:ms-iuikp1n1ydyfwncdqjd5wdoi>
            <sdc4:ms-cpq0lpgg887vpys05bucuep3>
                <label>State</label>
                <xdstring-value>California</xdstring-value>
            </sdc4:ms-cpq0lpgg887vpys05bucuep3>
        </sdc4:ms-iuikp1n1ydyfwncdqjd5wdoi>
        <sdc4:ms-ahfdavxt7dpx960rqi1qtb0l>
            <sdc4:ms-q1ey1sf5otsa97e76kb06hco>
                <label>Adult Population</label>
                <xdcount-value>not_a_number</xdcount-value>
                <xdcount-units>
                    <label>Count Units</label>
                    <xdstring-value>people</xdstring-value>
                </xdcount-units>
            </sdc4:ms-q1ey1sf5otsa97e76kb06hco>
        </sdc4:ms-ahfdavxt7dpx960rqi1qtb0l>
    </sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            validator = SDC4Validator(self.schema_path)
            result = validator.validate(xml_path)

            self.assertFalse(result.is_valid)
            # Should have semantic errors (type violation) but
            # may or may not have structural depending on schema strictness
            self.assertGreater(result.error_count, 0)
        finally:
            xml_path.unlink()

    def test_validate_structure_returns_structural_only(self):
        """validate_structure() returns only structural errors."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <UnknownElement>bad</UnknownElement>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            validator = SDC4Validator(self.schema_path)
            structural_errors = validator.validate_structure(xml_path)
            self.assertGreater(len(structural_errors), 0)
        finally:
            xml_path.unlink()

    def test_validate_structure_clean_document(self):
        """validate_structure() returns empty list for valid structure."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
    <sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
        <label>StatePopulation Data Cluster</label>
    </sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            validator = SDC4Validator(self.schema_path)
            structural_errors = validator.validate_structure(xml_path)
            self.assertEqual(len(structural_errors), 0)
        finally:
            xml_path.unlink()

    def test_validate_and_report(self):
        """validate_and_report() returns a structured report dict."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <UnknownElement>bad</UnknownElement>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            validator = SDC4Validator(self.schema_path)
            report = validator.validate_and_report(xml_path)

            self.assertFalse(report['valid'])
            self.assertGreater(report['error_count'], 0)
            self.assertIn('structural_errors', report)
            self.assertIn('semantic_errors', report)
        finally:
            xml_path.unlink()

    def test_validation_result_properties(self):
        """ValidationResult dataclass works correctly."""
        result = ValidationResult(is_valid=True)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)

        result2 = ValidationResult(
            is_valid=False,
            structural_errors=["err1"],
            semantic_errors=["err2", "err3"],
        )
        self.assertFalse(result2.is_valid)
        self.assertEqual(result2.error_count, 3)


if __name__ == '__main__':
    unittest.main()
