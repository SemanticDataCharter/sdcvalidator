"""
Tests for XML <-> JSON conversion.
"""

import json
import tempfile
from pathlib import Path

import pytest

from sdcvalidator.converters import xml_to_json, json_to_xml


TEST_DATA_DIR = Path(__file__).parent / 'test_data'
VALID_SCHEMA = TEST_DATA_DIR / 'valid_sdc4_schema.xsd'

SDC4_NS = "https://semanticdatacharter.com/ns/sdc4/"


class TestXmlToJson:
    """Tests for xml_to_json conversion."""

    def test_schema_aware_conversion(self):
        """Convert XML to JSON using schema for type awareness."""
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:Patient xmlns:sdc4="{SDC4_NS}">
    <sdc4:label>Patient Name</sdc4:label>
    <sdc4:xdstring-value>John Doe</sdc4:xdstring-value>
</sdc4:Patient>
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.xml', delete=False
        ) as f:
            f.write(xml_content)
            xml_path = f.name

        try:
            result = xml_to_json(xml_path, schema_path=VALID_SCHEMA)
            assert isinstance(result, dict)
            # xmlschema uses prefixed keys with elementFormDefault="qualified"
            assert result.get('sdc4:label') == 'Patient Name'
            assert result.get('sdc4:xdstring-value') == 'John Doe'
        finally:
            Path(xml_path).unlink()

    def test_requires_schema(self):
        """xml_to_json raises ValueError without schema."""
        with pytest.raises(ValueError, match="schema_path is required"):
            xml_to_json("dummy.xml")


class TestJsonToXml:
    """Tests for json_to_xml conversion."""

    def test_json_dict_to_xml(self):
        """Convert a JSON dict to XML using a schema."""
        # Use prefixed keys matching xmlschema's output format
        json_data = {
            '@xmlns:sdc4': SDC4_NS,
            'sdc4:label': 'Patient Name',
            'sdc4:xdstring-value': 'Jane Doe',
        }

        with tempfile.NamedTemporaryFile(
            suffix='.xml', delete=False
        ) as f:
            output_path = f.name

        try:
            json_to_xml(json_data, VALID_SCHEMA, output_path)
            assert Path(output_path).exists()
            content = Path(output_path).read_text()
            assert 'Jane Doe' in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_json_file_to_xml(self):
        """Convert a JSON file to XML."""
        json_data = {
            '@xmlns:sdc4': SDC4_NS,
            'sdc4:label': 'Patient Name',
            'sdc4:xdstring-value': 'Bob Smith',
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as jf:
            json.dump(json_data, jf)
            json_path = jf.name

        with tempfile.NamedTemporaryFile(
            suffix='.xml', delete=False
        ) as xf:
            output_path = xf.name

        try:
            json_to_xml(json_path, VALID_SCHEMA, output_path)
            assert Path(output_path).exists()
            content = Path(output_path).read_text()
            assert 'Bob Smith' in content
        finally:
            Path(json_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_roundtrip(self):
        """XML -> JSON -> XML roundtrip preserves data."""
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:Patient xmlns:sdc4="{SDC4_NS}">
    <sdc4:label>Patient Name</sdc4:label>
    <sdc4:xdstring-value>Roundtrip Test</sdc4:xdstring-value>
</sdc4:Patient>
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.xml', delete=False
        ) as f:
            f.write(xml_content)
            xml_path = f.name

        with tempfile.NamedTemporaryFile(
            suffix='.xml', delete=False
        ) as f:
            output_path = f.name

        try:
            # XML -> JSON
            data = xml_to_json(xml_path, schema_path=VALID_SCHEMA)
            assert data['sdc4:xdstring-value'] == 'Roundtrip Test'

            # JSON -> XML
            json_to_xml(data, VALID_SCHEMA, output_path)
            content = Path(output_path).read_text()
            assert 'Roundtrip Test' in content
        finally:
            Path(xml_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
