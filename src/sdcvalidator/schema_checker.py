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
SDC4 schema compliance validation.

Validates that XSD schemas follow SDC4 principles:
- No xsd:extension elements (only xsd:restriction allowed)
- Enforces separation of structure (reference model) and semantics (data models)
"""

from typing import List, Tuple, Union
from pathlib import Path
from xml.etree import ElementTree as ET

from .constants import SDC4_NAMESPACE


class SDC4SchemaValidationError(Exception):
    """Raised when a schema violates SDC4 principles."""
    pass


def validate_sdc4_schema_compliance(
    schema_path: Union[str, Path]
) -> Tuple[bool, List[str]]:
    """
    Validate that an XSD schema is SDC4-compliant.

    SDC4 data models must use xsd:restriction only, never xsd:extension.

    Args:
        schema_path: Path to the XSD schema file to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    schema_path = Path(schema_path)

    try:
        tree = ET.parse(schema_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return False, [f"Failed to parse schema: {e}"]
    except FileNotFoundError:
        return False, [f"Schema file not found: {schema_path}"]

    # Only validate SDC4 schemas
    target_namespace = root.get('targetNamespace')
    if target_namespace != SDC4_NAMESPACE:
        return True, []

    XSD_NS = 'http://www.w3.org/2001/XMLSchema'

    # Build parent map
    parent_map = {child: parent for parent in root.iter() for child in parent}

    errors = []

    for extension_elem in root.iter(f'{{{XSD_NS}}}extension'):
        base_type = extension_elem.get('base', 'unknown')
        type_elem = _find_containing_type(extension_elem, parent_map, XSD_NS)

        if type_elem is not None:
            type_name = type_elem.get('name', 'anonymous type')
            errors.append(
                f"xsd:extension found in type '{type_name}' extending '{base_type}'. "
                f"SDC4 data models must use xsd:restriction only, never xsd:extension. "
                f"This guarantees global interoperability and enforces separation of "
                f"structure (reference model) and semantics (data model)."
            )
        else:
            errors.append(
                f"xsd:extension found extending '{base_type}'. "
                f"SDC4 data models must use xsd:restriction only to guarantee "
                f"global interoperability."
            )

    if errors:
        return False, errors

    return True, []


def assert_sdc4_schema_compliance(schema_path: Union[str, Path]) -> None:
    """
    Assert that a schema is SDC4-compliant, raising exception if not.

    Args:
        schema_path: Path to the XSD schema file to validate

    Raises:
        SDC4SchemaValidationError: If schema violates SDC4 principles
    """
    is_valid, errors = validate_sdc4_schema_compliance(schema_path)

    if not is_valid:
        error_msg = (
            f"Schema '{schema_path}' violates SDC4 compliance:\n\n" +
            "\n".join(f"  - {error}" for error in errors) +
            "\n\nSDC4 Principle: Data models must use xsd:restriction (not xsd:extension) "
            "to guarantee global interoperability and enforce separation of structure and semantics."
        )
        raise SDC4SchemaValidationError(error_msg)


def _find_containing_type(
    element: ET.Element,
    parent_map: dict,
    xsd_namespace: str
) -> Union[ET.Element, None]:
    """Find the complexType or simpleType element that contains this element."""
    current = element

    while current is not None:
        parent = parent_map.get(current)
        if parent is None:
            break
        parent_tag = parent.tag
        if (parent_tag == f'{{{xsd_namespace}}}complexType' or
                parent_tag == f'{{{xsd_namespace}}}simpleType'):
            return parent
        current = parent

    return None
