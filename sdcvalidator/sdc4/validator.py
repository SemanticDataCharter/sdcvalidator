#
# Copyright (c), 2025, Axius-SDC, Inc.
# All rights reserved.
# This file is distributed under the terms of the MIT License.
#
"""
SDC4-aware validation with ExceptionalValue recovery.
"""

from typing import Union, Optional, Iterator, Dict, Any, List
from pathlib import Path
from xml.etree import ElementTree as ET
import copy

from sdcvalidator import XMLSchema11
from sdcvalidator.core.exceptions import XMLSchemaValidationError
from sdcvalidator.resources import XMLResource

from .error_mapper import ErrorMapper
from .instance_modifier import InstanceModifier
from .constants import ExceptionalValueType
from .schema_validator import validate_sdc4_schema_compliance, SDC4SchemaValidationError


class SDC4Validator:
    """
    Validates XML instances against SDC4 data model schemas and inserts
    ExceptionalValue elements for validation errors.

    Uses the SDC4 "quarantine-and-tag" pattern where invalid values are
    preserved and flagged with ExceptionalValue elements for data quality
    tracking and auditing.
    """

    def __init__(self, schema: Union[str, Path, XMLSchema11],
                 error_mapper: Optional[ErrorMapper] = None,
                 namespace_prefix: str = 'sdc4',
                 validation: str = 'lax',
                 check_sdc4_compliance: bool = True):
        """
        Initialize the SDC4 validator.

        :param schema: Path to the XSD schema file or an XMLSchema11 instance.
        :param error_mapper: Optional custom error mapper (default: uses ErrorMapper with default rules).
        :param namespace_prefix: The XML namespace prefix to use for SDC4 elements (default: 'sdc4').
        :param validation: Schema validation mode: 'strict', 'lax', or 'skip' (default: 'lax').
        :param check_sdc4_compliance: If True, validate that schema follows SDC4 principles (no xsd:extension).
                                       Default: True. Set to False to skip compliance check.
        :raises SDC4SchemaValidationError: If check_sdc4_compliance is True and schema violates SDC4 principles.
        """
        # Check SDC4 compliance before loading schema (if requested and schema is a path)
        if check_sdc4_compliance and isinstance(schema, (str, Path)):
            is_valid, errors = validate_sdc4_schema_compliance(schema)
            if not is_valid:
                error_msg = (
                    f"Schema violates SDC4 compliance:\n\n" +
                    "\n".join(f"  ❌ {error}" for error in errors) +
                    "\n\nSDC4 Principle: Data models must use xsd:restriction (not xsd:extension) "
                    "to guarantee global interoperability and enforce separation of structure and semantics."
                )
                raise SDC4SchemaValidationError(error_msg)

        # Load schema if it's a path
        if isinstance(schema, (str, Path)):
            self.schema = XMLSchema11(str(schema), validation=validation)
        else:
            self.schema = schema

        # Initialize mapper and modifier
        self.error_mapper = error_mapper or ErrorMapper()
        self.instance_modifier = InstanceModifier(namespace_prefix=namespace_prefix)

    def validate_with_recovery(self,
                                xml_source: Union[str, Path, ET.Element, XMLResource],
                                output_path: Optional[Union[str, Path]] = None,
                                remove_existing_ev: bool = True,
                                save: bool = True) -> ET.ElementTree:
        """
        Validate an XML instance and insert ExceptionalValue elements for errors.

        The recovered XML with ExceptionalValue tags is automatically saved unless save=False.

        :param xml_source: The XML instance to validate (file path, element, or XMLResource).
        :param output_path: Optional output file path. If None and xml_source is a file path,
                           defaults to '{original_filename}-ev.xml' in the same directory.
                           If xml_source is not a file path, you must provide output_path or set save=False.
        :param remove_existing_ev: If True, remove any existing ExceptionalValue elements before processing.
        :param save: If True (default), save the recovered XML to output_path. Set to False to skip saving.
        :return: Modified XML ElementTree with ExceptionalValue elements inserted.
        :raises ValueError: If save=True but output_path cannot be determined.

        Example usage:
            # Default: saves to 'count_error_example-ev.xml' in same directory
            validator.validate_with_recovery('count_error_example.xml')

            # Custom output path
            validator.validate_with_recovery('input.xml', output_path='/path/to/recovered.xml')

            # Don't save, just return the tree
            tree = validator.validate_with_recovery('input.xml', save=False)
        """
        # Track the original file path for default output naming
        original_file_path = None
        if isinstance(xml_source, (str, Path)):
            original_file_path = Path(xml_source)

        # Parse the XML if it's a path
        if isinstance(xml_source, (str, Path)):
            tree = ET.parse(str(xml_source))
            root = tree.getroot()
        elif isinstance(xml_source, ET.Element):
            root = xml_source
            tree = ET.ElementTree(root)
        elif isinstance(xml_source, XMLResource):
            root = xml_source.root
            tree = ET.ElementTree(root)
        else:
            raise TypeError(f"Unsupported xml_source type: {type(xml_source)}")

        # Make a copy to avoid modifying the original
        root = copy.deepcopy(root)
        tree = ET.ElementTree(root)

        # Optionally remove existing ExceptionalValue elements
        if remove_existing_ev:
            self.instance_modifier.remove_existing_exceptional_values(root)

        # Collect validation errors
        errors = list(self.schema.iter_errors(tree))

        # Process each error
        for error in errors:
            # Map error to ExceptionalValue type
            ev_type = self.error_mapper.map_error(error)

            # Skip if error mapper returned None (structural/metadata element)
            if ev_type is None:
                continue

            # Get the XPath to the error location
            xpath = error.path

            if xpath:
                # Insert the ExceptionalValue element
                success = self.instance_modifier.insert_exceptional_value(
                    root=root,
                    xpath=xpath,
                    ev_type=ev_type,
                    reason=error.reason
                )

                if not success:
                    # Log or handle insertion failure
                    # For now, we'll just continue
                    pass

        # Save the recovered XML if requested
        if save:
            # Determine output path
            if output_path is None:
                if original_file_path is None:
                    raise ValueError(
                        "Cannot determine output path: xml_source is not a file path. "
                        "Either provide output_path parameter or set save=False."
                    )
                # Default naming: {original_filename}-ev.xml
                output_path = original_file_path.parent / f"{original_file_path.stem}-ev{original_file_path.suffix}"
            else:
                output_path = Path(output_path)

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with formatting
            ET.indent(tree, space='    ')
            tree.write(str(output_path), encoding='UTF-8', xml_declaration=True)

        return tree

    def iter_errors_with_mapping(self,
                                   xml_source: Union[str, Path, ET.Element, XMLResource]
                                   ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over validation errors with their mapped ExceptionalValue types.

        :param xml_source: The XML instance to validate.
        :yield: Dictionaries containing error details and mapped ExceptionalValue type.
        """
        # Parse the XML if needed
        if isinstance(xml_source, (str, Path)):
            tree = ET.parse(str(xml_source))
        elif isinstance(xml_source, ET.Element):
            tree = ET.ElementTree(xml_source)
        elif isinstance(xml_source, XMLResource):
            tree = ET.ElementTree(xml_source.root)
        else:
            raise TypeError(f"Unsupported xml_source type: {type(xml_source)}")

        # Collect validation errors
        for error in self.schema.iter_errors(tree):
            # Map error to ExceptionalValue type
            ev_type = self.error_mapper.map_error(error)

            # Skip if error mapper returned None (structural/metadata element)
            # These errors cannot be recovered with ExceptionalValue
            if ev_type is None:
                continue

            # Generate summary
            summary = self.error_mapper.get_error_summary(error, ev_type)

            yield summary

    def validate_and_report(self,
                            xml_source: Union[str, Path, ET.Element, XMLResource]
                            ) -> Dict[str, Any]:
        """
        Validate an XML instance and return a detailed report.

        :param xml_source: The XML instance to validate.
        :return: Dictionary containing validation results and error summaries.
        """
        errors = list(self.iter_errors_with_mapping(xml_source))

        report = {
            'valid': len(errors) == 0,
            'error_count': len(errors),
            'errors': errors
        }

        # Group errors by ExceptionalValue type
        ev_type_counts: Dict[str, int] = {}
        for error in errors:
            ev_code = error['exceptional_value_type']
            ev_type_counts[ev_code] = ev_type_counts.get(ev_code, 0) + 1

        report['exceptional_value_type_counts'] = ev_type_counts

        return report

    def save_recovered_xml(self,
                           output_path: Union[str, Path],
                           xml_source: Union[str, Path, ET.Element, XMLResource],
                           remove_existing_ev: bool = True,
                           encoding: str = 'UTF-8',
                           xml_declaration: bool = True):
        """
        Validate an XML instance, insert ExceptionalValues, and save to file.

        :param output_path: Path where the modified XML should be saved.
        :param xml_source: The XML instance to validate.
        :param remove_existing_ev: If True, remove any existing ExceptionalValue elements.
        :param encoding: XML encoding (default: 'UTF-8').
        :param xml_declaration: Include XML declaration (default: True).
        """
        # Perform recovery
        recovered_tree = self.validate_with_recovery(xml_source, remove_existing_ev)

        # Save to file
        recovered_tree.write(
            str(output_path),
            encoding=encoding,
            xml_declaration=xml_declaration,
            method='xml'
        )


def validate_with_recovery(schema_path: Union[str, Path],
                            xml_path: Union[str, Path],
                            output_path: Optional[Union[str, Path]] = None,
                            **kwargs) -> ET.ElementTree:
    """
    Convenience function to validate an XML file and insert ExceptionalValues.

    :param schema_path: Path to the XSD schema file.
    :param xml_path: Path to the XML instance file.
    :param output_path: Optional path to save the recovered XML (if None, doesn't save).
    :param kwargs: Additional arguments to pass to SDC4Validator.
    :return: Modified XML ElementTree with ExceptionalValue elements inserted.
    """
    validator = SDC4Validator(schema_path, **kwargs)
    recovered_tree = validator.validate_with_recovery(xml_path)

    if output_path:
        recovered_tree.write(str(output_path), encoding='UTF-8', xml_declaration=True)

    return recovered_tree
