"""
Instances that fill a declared type through ``xsi:type``.

The SDC4 reference model declares ``sdc4:XdOrdinal`` and its siblings
abstract, so a schema-valid instance fills them with a concrete type through
``xsi:type="sdc4:XdOrdinalType"``. Before 4.5.1 every input was normalised
into a stdlib ElementTree, which drops the namespace prefix declarations;
the prefixed QName in ``xsi:type`` then could not be resolved and xmlschema
raised ``XMLSchemaKeyError`` instead of validating. A path or an XMLResource
carries the declarations and must validate.
"""

import io
import unittest
from pathlib import Path

from xmlschema import XMLResource

from sdcvalidator.validator import SDC4Validator

DATA = Path(__file__).parent / "test_data"
SCHEMA = DATA / "xsi_type_schema.xsd"
VALID = DATA / "xsi_type_instance.xml"
INVALID = DATA / "xsi_type_instance_invalid.xml"


class TestXsiTypeResolution(unittest.TestCase):
    def setUp(self):
        self.validator = SDC4Validator(SCHEMA, check_sdc4_compliance=False)

    def test_a_path_validates(self):
        result = self.validator.validate(str(VALID))
        self.assertTrue(result.is_valid, result.structural_errors + result.semantic_errors)

    def test_a_pathlib_path_validates(self):
        self.assertTrue(self.validator.validate(VALID).is_valid)

    def test_an_xmlresource_over_bytes_validates(self):
        resource = XMLResource(io.BytesIO(VALID.read_bytes()))
        self.assertTrue(self.validator.validate(resource).is_valid)

    def test_the_report_and_recovery_paths_resolve_the_type_too(self):
        report = self.validator.validate_and_report(str(VALID))
        self.assertTrue(report["valid"], report)
        self.assertEqual(report["error_count"], 0)
        self.validator.validate_with_recovery(str(VALID), save=False)
        self.assertEqual(self.validator.validate_structure(str(VALID)), [])
        self.assertEqual(self.validator.iter_errors(str(VALID)), [])

    def test_a_type_that_resolves_is_still_checked(self):
        """Resolving the type must not mean skipping it: a bad ordinal is caught."""
        result = self.validator.validate(str(INVALID))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        report = self.validator.validate_and_report(XMLResource(io.BytesIO(INVALID.read_bytes())))
        self.assertEqual(report["error_count"], 1)


if __name__ == "__main__":
    unittest.main()
