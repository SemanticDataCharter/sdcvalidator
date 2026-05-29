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
SDC4 structural validator with ExceptionalValue recovery.

Two-tier validation:
  - Tier 1 (structural): unknown elements, wrong nesting, cardinality -> REJECT
  - Tier 2 (semantic): type/pattern/range violations -> quarantine-and-tag with
    an ISO 21090 ExceptionalValue (recovery).
"""

import copy
import logging
from typing import Union, Dict, Any, List, Optional, Iterator
from pathlib import Path
from xml.etree import ElementTree as ET
from dataclasses import dataclass, field

from xmlschema import XMLSchema11, XMLResource
from xmlschema.validators.exceptions import XMLSchemaValidationError

from .error_classifier import ErrorClassifier
from .error_mapper import ErrorMapper
from .instance_modifier import InstanceModifier
from .exceptions import SDC4StructuralValidationError
from .schema_checker import (
    validate_sdc4_schema_compliance,
    SDC4SchemaValidationError
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating an XML document against an SDC4 schema."""
    is_valid: bool
    structural_errors: List[XMLSchemaValidationError] = field(default_factory=list)
    semantic_errors: List[XMLSchemaValidationError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.structural_errors) + len(self.semantic_errors)


class SDC4Validator:
    """
    Validates XML instances against SDC4 data model schemas.

    Classifies errors into structural (Tier 1) and semantic (Tier 2) categories,
    and can recover semantic errors with the SDC4 "quarantine-and-tag" pattern:
    invalid values are preserved and flagged with ExceptionalValue elements
    (ISO 21090 NULL Flavors) for data-quality tracking and auditing.
    """

    def __init__(
        self,
        schema: Union[str, Path, XMLSchema11],
        check_sdc4_compliance: bool = True,
        validation: str = 'strict',
        error_mapper: Optional[ErrorMapper] = None,
        namespace_prefix: str = 'sdc4',
    ):
        """
        Initialize the SDC4 validator.

        Args:
            schema: Path to XSD schema file or an XMLSchema11 instance.
            check_sdc4_compliance: If True, validate schema follows SDC4
                principles (no xsd:extension). Default: True.
            validation: Schema validation mode ('strict', 'lax', 'skip').
                Default is 'strict' to catch invalid restriction derivations
                (e.g. wrong element names, type mismatches). Lax mode silently
                accepts these errors.
            error_mapper: Optional custom ErrorMapper for error->ExceptionalValue
                mapping. Defaults to an ErrorMapper sharing this validator's
                classifier so the tiering decision is made in one place.
            namespace_prefix: XML namespace prefix for inserted SDC4 elements.

        Raises:
            SDC4SchemaValidationError: If compliance check fails.
        """
        if check_sdc4_compliance and isinstance(schema, (str, Path)):
            is_valid, errors = validate_sdc4_schema_compliance(schema)
            if not is_valid:
                error_msg = (
                    "Schema violates SDC4 compliance:\n\n" +
                    "\n".join(f"  - {error}" for error in errors) +
                    "\n\nSDC4 Principle: Data models must use xsd:restriction "
                    "(not xsd:extension) to guarantee global interoperability "
                    "and enforce separation of structure and semantics."
                )
                raise SDC4SchemaValidationError(error_msg)

        if isinstance(schema, (str, Path)):
            self.schema = XMLSchema11(str(schema), validation=validation)
        else:
            self.schema = schema

        self.classifier = ErrorClassifier()
        # ErrorMapper shares the classifier so tiering is decided in one place.
        self.error_mapper = error_mapper or ErrorMapper(classifier=self.classifier)
        self.instance_modifier = InstanceModifier(namespace_prefix=namespace_prefix)

    # ------------------------------------------------------------------ #
    # Input handling
    # ------------------------------------------------------------------ #

    def _to_tree(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> ET.ElementTree:
        """
        Normalize a supported XML source into an ElementTree.

        Accepts a file path (str/Path), an ElementTree.Element, or an
        xmlschema.XMLResource.
        """
        if isinstance(xml_source, (str, Path)):
            return ET.parse(str(xml_source))
        elif isinstance(xml_source, ET.Element):
            return ET.ElementTree(xml_source)
        elif isinstance(xml_source, XMLResource):
            return ET.ElementTree(xml_source.root)
        else:
            raise TypeError(f"Unsupported xml_source type: {type(xml_source)}")

    # ------------------------------------------------------------------ #
    # Classification-only validation (no modification)
    # ------------------------------------------------------------------ #

    def validate(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> ValidationResult:
        """
        Validate an XML instance and classify all errors.

        Returns:
            ValidationResult with is_valid, structural_errors, semantic_errors.
        """
        tree = self._to_tree(xml_source)
        errors = list(self.schema.iter_errors(tree))

        classified = self.classifier.classify_all(errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            structural_errors=classified["structural"],
            semantic_errors=classified["semantic"],
        )

    def validate_structure(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> List[XMLSchemaValidationError]:
        """
        Validate XML structure only (Tier 1 validation).

        Returns:
            List of structural errors. Empty list means structure is valid.
        """
        tree = self._to_tree(xml_source)
        errors = list(self.schema.iter_errors(tree))
        return [e for e in errors if self.classifier.is_structural_error(e)]

    def iter_errors(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> List[Dict[str, str]]:
        """
        Iterate over all validation errors with classification.

        Returns:
            List of error summary dictionaries (structural and semantic).
        """
        tree = self._to_tree(xml_source)
        errors = list(self.schema.iter_errors(tree))
        return [self.classifier.get_error_summary(e) for e in errors]

    def iter_errors_with_mapping(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over validation errors with their mapped ExceptionalValue types.

        Structural-element errors (which cannot be recovered) are skipped.

        Yields:
            Dictionaries containing error details and the mapped EV type.
        """
        tree = self._to_tree(xml_source)
        for error in self.schema.iter_errors(tree):
            ev_type = self.error_mapper.map_error(error)
            if ev_type is None:
                continue
            yield self.error_mapper.get_error_summary(error, ev_type)

    def validate_and_report(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> Dict[str, Any]:
        """
        Validate an XML instance and return a detailed report.

        The report is a superset that serves both the structural/semantic
        breakdown and the flat error list (with ExceptionalValue mapping)
        that consumers rely on.

        Returns:
            Dictionary with keys: valid, error_count, structural_error_count,
            semantic_error_count, structural_errors, semantic_errors, errors,
            exceptional_value_type_counts.
        """
        result = self.validate(xml_source)

        structural_summaries = [
            self.classifier.get_error_summary(e) for e in result.structural_errors
        ]
        semantic_summaries = [
            self.classifier.get_error_summary(e) for e in result.semantic_errors
        ]

        mapped_errors = list(self.iter_errors_with_mapping(xml_source))

        ev_type_counts: Dict[str, int] = {}
        for err in mapped_errors:
            code = err.get('exceptional_value_type')
            if code:
                ev_type_counts[code] = ev_type_counts.get(code, 0) + 1

        return {
            'valid': result.is_valid,
            'error_count': result.error_count,
            'structural_error_count': len(result.structural_errors),
            'semantic_error_count': len(result.semantic_errors),
            'structural_errors': structural_summaries,
            'semantic_errors': semantic_summaries,
            'errors': mapped_errors,
            'exceptional_value_type_counts': ev_type_counts,
        }

    # ------------------------------------------------------------------ #
    # ExceptionalValue recovery (quarantine-and-tag)
    # ------------------------------------------------------------------ #

    def validate_with_recovery(
        self,
        xml_source: Union[str, Path, ET.Element, XMLResource],
        output_path: Optional[Union[str, Path]] = None,
        remove_existing_ev: bool = True,
        save: bool = True,
    ) -> ET.ElementTree:
        """
        Validate an XML instance and insert ExceptionalValue elements for errors.

        Tier 1 (structural) errors cause a hard reject (SDC4StructuralValidationError).
        Tier 2 (semantic) errors are quarantined with ExceptionalValue tags.

        The recovered XML is saved unless save=False. When saving and no
        output_path is given, defaults to '{stem}-ev{suffix}' beside the input.

        Returns:
            Modified XML ElementTree with ExceptionalValue elements inserted.

        Raises:
            SDC4StructuralValidationError: If structural (Tier 1) errors are present.
            ValueError: If save=True but output_path cannot be determined.
        """
        original_file_path = None
        if isinstance(xml_source, (str, Path)):
            original_file_path = Path(xml_source)

        tree = self._to_tree(xml_source)
        # Work on a deep copy so the caller's source is never mutated.
        root = copy.deepcopy(tree.getroot())
        tree = ET.ElementTree(root)

        if remove_existing_ev:
            self.instance_modifier.remove_existing_exceptional_values(root)

        errors = list(self.schema.iter_errors(tree))

        structural_errors = []
        semantic_errors = []
        for error in errors:
            if self.error_mapper.is_structural_error(error):
                structural_errors.append(error)
            else:
                semantic_errors.append(error)

        # Tier 1: hard reject.
        if structural_errors:
            raise SDC4StructuralValidationError(structural_errors)

        # Tier 2: quarantine-and-tag.
        for error in semantic_errors:
            ev_type = self.error_mapper.map_error(error)
            if ev_type is None:
                continue
            xpath = error.path
            if xpath:
                success = self.instance_modifier.insert_exceptional_value(
                    root=root,
                    xpath=xpath,
                    ev_type=ev_type,
                    reason=error.reason,
                )
                if not success:
                    logger.warning(
                        "Failed to insert ExceptionalValue at xpath '%s': %s",
                        xpath, error.reason,
                    )

        if save:
            if output_path is None:
                if original_file_path is None:
                    raise ValueError(
                        "Cannot determine output path: xml_source is not a file path. "
                        "Either provide output_path or set save=False."
                    )
                output_path = (
                    original_file_path.parent
                    / f"{original_file_path.stem}-ev{original_file_path.suffix}"
                )
            else:
                output_path = Path(output_path)

            # Prevent path traversal via '..' components.
            try:
                output_path.resolve().relative_to(output_path.parent.resolve())
            except ValueError:
                raise ValueError(
                    f"Output path '{output_path}' resolves outside its parent directory"
                )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            ET.indent(tree, space='    ')
            tree.write(str(output_path), encoding='UTF-8', xml_declaration=True)

        return tree

    def save_recovered_xml(
        self,
        output_path: Union[str, Path],
        xml_source: Union[str, Path, ET.Element, XMLResource],
        remove_existing_ev: bool = True,
        encoding: str = 'UTF-8',
        xml_declaration: bool = True,
    ):
        """
        Validate an XML instance, insert ExceptionalValues, and save to file
        with a caller-chosen encoding.
        """
        recovered_tree = self.validate_with_recovery(
            xml_source,
            remove_existing_ev=remove_existing_ev,
            save=False,
        )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        recovered_tree.write(
            str(output_path),
            encoding=encoding,
            xml_declaration=xml_declaration,
            method='xml',
        )


def validate_with_recovery(
    schema_path: Union[str, Path],
    xml_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    **kwargs,
) -> ET.ElementTree:
    """
    Convenience function: validate an XML file and insert ExceptionalValues.

    :param schema_path: Path to the XSD schema file.
    :param xml_path: Path to the XML instance file.
    :param output_path: Optional path to save the recovered XML.
    :param kwargs: Additional arguments forwarded to SDC4Validator.
    :return: Modified XML ElementTree with ExceptionalValue elements inserted.
    """
    validator = SDC4Validator(schema_path, **kwargs)
    recovered_tree = validator.validate_with_recovery(xml_path, save=False)

    if output_path:
        recovered_tree.write(str(output_path), encoding='UTF-8', xml_declaration=True)

    return recovered_tree
