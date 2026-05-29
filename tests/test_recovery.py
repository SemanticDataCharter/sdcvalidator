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
Integration tests for SDC4 validation with ExceptionalValue recovery.
"""

import unittest
import tempfile
from pathlib import Path

from sdcvalidator import SDC4Validator, EXCEPTIONAL_VALUE_TYPES


class TestSDC4Recovery(unittest.TestCase):
    """Integration tests using the SDC4 example data model."""

    def setUp(self):
        self.schema_path = Path(__file__).parent / 'test_data' / 'dm-jsi5yxnvzsmsisgn2bvelkni.xsd'
        if not self.schema_path.exists():
            self.skipTest(f"SDC4 example schema not found at {self.schema_path}")

    def _validator(self):
        # 'lax' schema-build mode mirrors the recovery flow's historical default.
        return SDC4Validator(self.schema_path, validation='lax')

    def test_report_has_superset_keys(self):
        """validate_and_report returns both the structural/semantic breakdown
        and the flat 'errors' list consumers rely on."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)
        try:
            report = self._validator().validate_and_report(xml_path)
            # vaas-shaped keys
            self.assertIn('valid', report)
            self.assertIn('error_count', report)
            self.assertIsInstance(report['errors'], list)
            # FOSS-shaped keys (back-compat)
            self.assertIn('structural_errors', report)
            self.assertIn('semantic_errors', report)
            self.assertIn('exceptional_value_type_counts', report)
        finally:
            xml_path.unlink()

    def test_invalid_type_recovery_inserts_ev(self):
        """A bad xdcount-value is quarantined with an ExceptionalValue element."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
    <sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
        <label>StatePopulation Data Cluster</label>
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
            recovered_tree = self._validator().validate_with_recovery(xml_path, save=False)
            ev_codes = set(EXCEPTIONAL_VALUE_TYPES.keys())
            found = {
                (elem.tag.split('}')[1] if '}' in elem.tag else elem.tag)
                for elem in recovered_tree.getroot().iter()
                if isinstance(elem.tag, str)  # skip comment/PI nodes (non-str tag)
            }
            self.assertTrue(found & ev_codes,
                            "expected at least one ExceptionalValue element after recovery")
        finally:
            xml_path.unlink()

    def test_error_mapping_report_shape(self):
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni
    xmlns:sdc4="https://semanticdatacharter.com/ns/sdc4/">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)
        try:
            errors = list(self._validator().iter_errors_with_mapping(xml_path))
            for error in errors:
                self.assertIn('xpath', error)
                self.assertIn('error_type', error)
                self.assertIn('exceptional_value_type', error)
                self.assertIn('exceptional_value_name', error)
        finally:
            xml_path.unlink()

    def test_round_trip_preserves_structure(self):
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
            recovered_tree = self._validator().validate_with_recovery(xml_path, save=False)
            root = recovered_tree.getroot()
            local_name = root.tag.split('}')[1] if '}' in root.tag else root.tag
            self.assertEqual(local_name, 'dm-jsi5yxnvzsmsisgn2bvelkni')
            dm_label = root.find('.//dm-label')
            if dm_label is not None:
                self.assertEqual(dm_label.text, 'StatePopulation')
        finally:
            xml_path.unlink()


if __name__ == '__main__':
    unittest.main()
