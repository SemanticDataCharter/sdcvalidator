#
# Copyright (c), 2025, Axius-SDC, Inc.
# All rights reserved.
# This file is distributed under the terms of the MIT License.
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
    This enforces separation of structure (from reference model) and
    semantics (from data models).

    Args:
        schema_path: Path to the XSD schema file to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)
        - is_valid: True if schema is SDC4-compliant, False otherwise
        - list_of_error_messages: List of human-readable error descriptions

    Example:
        >>> is_valid, errors = validate_sdc4_schema_compliance('my_schema.xsd')
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"Error: {error}")
    """
    schema_path = Path(schema_path)

    # Parse the schema
    try:
        tree = ET.parse(schema_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return False, [f"Failed to parse schema: {e}"]
    except FileNotFoundError:
        return False, [f"Schema file not found: {schema_path}"]

    # Check if this is an SDC4 schema by checking targetNamespace
    target_namespace = root.get('targetNamespace')

    # Only validate SDC4 schemas (those with SDC4 target namespace)
    if target_namespace != SDC4_NAMESPACE:
        # Not an SDC4 schema, no validation needed
        return True, []

    # Define XSD namespace
    XSD_NS = 'http://www.w3.org/2001/XMLSchema'

    # Build parent map for efficient parent lookups
    parent_map = {child: parent for parent in root.iter() for child in parent}

    # Find all xsd:extension elements
    errors = []

    # Search for extension elements in both simple and complex content
    for extension_elem in root.iter(f'{{{XSD_NS}}}extension'):
        # Get the base type being extended
        base_type = extension_elem.get('base', 'unknown')

        # Try to find the containing type definition
        type_elem = _find_containing_type(extension_elem, parent_map, XSD_NS)

        if type_elem is not None:
            type_name = type_elem.get('name', 'anonymous type')

            # Get the line number if available (for better error messages)
            line_info = f" (line {extension_elem.sourceline})" if hasattr(extension_elem, 'sourceline') else ""

            errors.append(
                f"xsd:extension found in type '{type_name}' extending '{base_type}'{line_info}. "
                f"SDC4 data models must use xsd:restriction only, never xsd:extension. "
                f"This guarantees global interoperability and enforces separation of structure (reference model) and semantics (data model)."
            )
        else:
            # Fallback if we can't find the type name
            errors.append(
                f"xsd:extension found extending '{base_type}'. "
                f"SDC4 data models must use xsd:restriction only to guarantee global interoperability."
            )

    if errors:
        return False, errors

    return True, []


def assert_sdc4_schema_compliance(schema_path: Union[str, Path]) -> None:
    """
    Assert that a schema is SDC4-compliant, raising exception if not.

    This is a convenience function that calls validate_sdc4_schema_compliance()
    and raises an exception if the schema is not compliant.

    Args:
        schema_path: Path to the XSD schema file to validate

    Raises:
        SDC4SchemaValidationError: If schema violates SDC4 principles

    Example:
        >>> try:
        ...     assert_sdc4_schema_compliance('my_schema.xsd')
        ...     print("Schema is SDC4-compliant!")
        ... except SDC4SchemaValidationError as e:
        ...     print(f"Schema validation failed: {e}")
    """
    is_valid, errors = validate_sdc4_schema_compliance(schema_path)

    if not is_valid:
        error_msg = (
            f"Schema '{schema_path}' violates SDC4 compliance:\n\n" +
            "\n".join(f"  ❌ {error}" for error in errors) +
            "\n\nSDC4 Principle: Data models must use xsd:restriction (not xsd:extension) "
            "to guarantee global interoperability and enforce separation of structure and semantics."
        )
        raise SDC4SchemaValidationError(error_msg)


def _find_containing_type(
    element: ET.Element,
    parent_map: dict,
    xsd_namespace: str
) -> Union[ET.Element, None]:
    """
    Find the complexType or simpleType element that contains this element.

    Args:
        element: The XML element to search from
        parent_map: Dictionary mapping child elements to their parents
        xsd_namespace: The XSD namespace URI

    Returns:
        The containing type element, or None if not found
    """
    # Walk up the tree looking for complexType or simpleType
    current = element

    while current is not None:
        # Get parent from the parent map
        parent = parent_map.get(current)

        if parent is None:
            break

        parent_tag = parent.tag
        if parent_tag == f'{{{xsd_namespace}}}complexType' or parent_tag == f'{{{xsd_namespace}}}simpleType':
            return parent

        current = parent

    return None
