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
SDC4 structural validator — classify errors only, no recovery/injection.
"""

from typing import Union, Dict, Any, List
from pathlib import Path
from xml.etree import ElementTree as ET
from dataclasses import dataclass, field

from xmlschema import XMLSchema11
from xmlschema.validators.exceptions import XMLSchemaValidationError

from .error_classifier import ErrorClassifier
from .constants import ErrorTier
from .schema_checker import (
    validate_sdc4_schema_compliance,
    SDC4SchemaValidationError
)


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

    Classifies errors into structural (Tier 1) and semantic (Tier 2)
    categories. Does NOT perform EV injection or recovery — that is
    a commercial feature in sdcstudio-vaas.
    """

    def __init__(
        self,
        schema: Union[str, Path, XMLSchema11],
        check_sdc4_compliance: bool = True,
        validation: str = 'lax',
    ):
        """
        Initialize the SDC4 validator.

        Args:
            schema: Path to XSD schema file or an XMLSchema11 instance.
            check_sdc4_compliance: If True, validate schema follows SDC4
                principles (no xsd:extension). Default: True.
            validation: Schema validation mode ('strict', 'lax', 'skip').

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

    def validate(
        self, xml_source: Union[str, Path]
    ) -> ValidationResult:
        """
        Validate an XML instance and classify all errors.

        Args:
            xml_source: Path to the XML instance file.

        Returns:
            ValidationResult with is_valid, structural_errors, semantic_errors.
        """
        tree = ET.parse(str(xml_source))
        errors = list(self.schema.iter_errors(tree))

        classified = self.classifier.classify_all(errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            structural_errors=classified["structural"],
            semantic_errors=classified["semantic"],
        )

    def validate_structure(
        self, xml_source: Union[str, Path]
    ) -> List[XMLSchemaValidationError]:
        """
        Validate XML structure only (Tier 1 validation).

        Args:
            xml_source: Path to the XML instance file.

        Returns:
            List of structural errors. Empty list means structure is valid.
        """
        tree = ET.parse(str(xml_source))
        errors = list(self.schema.iter_errors(tree))
        return [e for e in errors if self.classifier.is_structural_error(e)]

    def validate_and_report(
        self, xml_source: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Validate an XML instance and return a detailed report.

        Args:
            xml_source: Path to the XML instance file.

        Returns:
            Dictionary containing validation results.
        """
        result = self.validate(xml_source)

        structural_summaries = [
            self.classifier.get_error_summary(e) for e in result.structural_errors
        ]
        semantic_summaries = [
            self.classifier.get_error_summary(e) for e in result.semantic_errors
        ]

        return {
            'valid': result.is_valid,
            'error_count': result.error_count,
            'structural_error_count': len(result.structural_errors),
            'semantic_error_count': len(result.semantic_errors),
            'structural_errors': structural_summaries,
            'semantic_errors': semantic_summaries,
        }

    def iter_errors(
        self, xml_source: Union[str, Path]
    ) -> List[Dict[str, str]]:
        """
        Iterate over all validation errors with classification.

        Args:
            xml_source: Path to the XML instance file.

        Returns:
            List of error summary dictionaries.
        """
        tree = ET.parse(str(xml_source))
        errors = list(self.schema.iter_errors(tree))
        return [self.classifier.get_error_summary(e) for e in errors]
