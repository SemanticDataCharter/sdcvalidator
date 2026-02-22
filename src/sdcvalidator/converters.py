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
XML <-> JSON conversion using xmlschema's schema-aware conversion.
"""

import json
from typing import Union, Optional, Dict, Any
from pathlib import Path
from xml.etree import ElementTree as ET

from xmlschema import XMLSchema11


def xml_to_json(
    xml_path: Union[str, Path],
    schema_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Convert an XML document to a JSON-compatible dictionary.

    Uses schema-aware conversion when a schema is provided for accurate
    type mapping.

    Args:
        xml_path: Path to the XML file.
        schema_path: Path to XSD schema for type-aware conversion (required).

    Returns:
        Dictionary representation of the XML document.
        Keys may include namespace prefixes (e.g. 'sdc4:label').

    Raises:
        ValueError: If no schema_path is provided.
    """
    if schema_path is None:
        raise ValueError("schema_path is required for xml_to_json conversion")

    schema = XMLSchema11(str(schema_path))
    return schema.to_dict(str(xml_path))


def json_to_xml(
    json_data: Union[Dict[str, Any], str, Path],
    schema_path: Union[str, Path],
    output_path: Union[str, Path],
    encoding: str = 'UTF-8',
) -> None:
    """
    Convert JSON data to an XML document using a schema for structure.

    Args:
        json_data: Dictionary, JSON string, or path to JSON file.
            Keys should match the format returned by xml_to_json
            (may include namespace prefixes).
        schema_path: Path to XSD schema defining the XML structure.
        output_path: Path where the XML output will be written.
        encoding: XML encoding (default: 'UTF-8').
    """
    # Load JSON data if it's a file path or string
    if isinstance(json_data, (str, Path)):
        data_path = Path(json_data)
        if data_path.exists():
            with open(data_path) as f:
                json_data = json.load(f)
        elif isinstance(json_data, str):
            json_data = json.loads(json_data)

    schema = XMLSchema11(str(schema_path))
    element = schema.encode(json_data)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(element, ET.Element):
        tree = ET.ElementTree(element)
        ET.indent(tree, space='    ')
        tree.write(str(output_path), encoding=encoding, xml_declaration=True)
    else:
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(str(element))
