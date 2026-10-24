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

from .xsd11_restriction import build_xsd11_schema
from xmlschema.validators.exceptions import XMLSchemaValidationError

from .error_classifier import ErrorClassifier
from .error_mapper import ErrorMapper
from .instance_modifier import InstanceModifier
from .exceptions import SDC4StructuralValidationError, SDC4UnrecoverableError
from .constants import EXCEPTIONAL_VALUE_CODES, ExceptionalValueType
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


@dataclass
class Recovery:
    """One value an ExceptionalValue covers after recovery."""
    path: str              # the Clark-form path of the element whose value failed (as xmlschema reports it)
    code: str              # the ISO 21090 code: "INV"
    name: str              # its name: "Invalid"
    reason: str            # what failed, from the validator: the constraint, the pattern, the type
    inserted: bool         # True if recovery inserted the ExceptionalValue; False if the record already carried one


@dataclass
class RecoveryResult:
    """What `SDC4Validator.recover()` did: the recovered tree, each value it covered, and each error it could not."""
    tree: ET.ElementTree
    recoveries: List[Recovery] = field(default_factory=list)
    unrecoverable: List[XMLSchemaValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when every error is covered by an ExceptionalValue."""
        return not self.unrecoverable

    @property
    def inserted(self) -> List[Recovery]:
        return [r for r in self.recoveries if r.inserted]


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
            # build_xsd11_schema preserves strict validation for every case except
            # the valid XSD 1.1 substitution-group restriction that xmlschema
            # false-rejects at build time (see xsd11_restriction).
            self.schema = build_xsd11_schema(str(schema), validation=validation)
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

    def _namespaces(
        self, xml_source: Union[str, Path, ET.Element, XMLResource]
    ) -> Optional[Dict[str, str]]:
        """
        The prefix map declared in the source, or None when it is not known.

        ``_to_tree`` normalises every source into a stdlib ElementTree, which
        resolves prefixes to Clark notation and discards the declarations. A
        prefixed QName that appears as *content* rather than as a tag, which
        is what ``xsi:type="sdc4:XdOrdinalType"`` is, can then no longer be
        resolved and xmlschema raises ``XMLSchemaKeyError`` instead of
        validating. The reference model relies on ``xsi:type`` wherever an
        abstract element is filled by a concrete type, so an instance that is
        valid against the reference model failed here before 4.5.1.

        A path or an XMLResource still carries the declarations, so they are
        read back and handed to xmlschema. A bare ``ET.Element`` has already
        lost them; callers validating such an instance should pass the path
        or an ``XMLResource`` instead.
        """
        if isinstance(xml_source, XMLResource):
            return xml_source.get_namespaces(root_only=False)
        if isinstance(xml_source, (str, Path)):
            return XMLResource(str(xml_source)).get_namespaces(root_only=False)
        return None

    def _schema_errors(
        self,
        tree: ET.ElementTree,
        xml_source: Union[str, Path, ET.Element, XMLResource],
    ) -> Iterator[XMLSchemaValidationError]:
        """
        xmlschema's errors over ``tree``, with the source's prefix map.

        The map is for resolving prefixed QNames in content during validation.
        It is removed from each error afterwards so ``error.path`` keeps its
        Clark form (``/{uri}local/...``): the recovery step locates elements by
        that form, and every report has always carried it.
        """
        namespaces = self._namespaces(xml_source)
        for error in self.schema.iter_errors(tree, namespaces=namespaces):
            error.namespaces = None
            error._path = None
            yield error

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
        errors = list(self._schema_errors(tree, xml_source))

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
        errors = list(self._schema_errors(tree, xml_source))
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
        errors = list(self._schema_errors(tree, xml_source))
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
        for error in self._schema_errors(tree, xml_source):
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

    def recover(
        self,
        xml_source: Union[str, Path, ET.Element, XMLResource],
        remove_existing_ev: bool = False,
    ) -> RecoveryResult:
        """
        Validate an XML instance and cover each semantic error with an ExceptionalValue.

        Tier 1 (structural) errors cause a hard reject (SDC4StructuralValidationError).
        Tier 2 (semantic) errors are quarantined: the value stays in the record and an
        ExceptionalValue is inserted beside it, once per value. A value whose element
        already carries an ExceptionalValue (one written where the record was made: a
        refusal, a masked field) is covered by it; nothing is inserted and nothing is
        removed. An error that cannot be covered (no ExceptionalValue maps to it, or
        the element cannot be found) is returned in `unrecoverable`, never skipped.

        Args:
            xml_source: A path, an Element, or an XMLResource (use an XMLResource when
                the instance carries prefixed QNames in content, such as xsi:type).
            remove_existing_ev: Remove every ExceptionalValue already in the record
                first. Off by default since 4.6.0: those written at the source are
                data, and removing them loses why a value is missing.

        Returns:
            RecoveryResult: the recovered tree (a copy; the source is never mutated),
            the recoveries, and the unrecoverable errors.

        Raises:
            SDC4StructuralValidationError: If structural (Tier 1) errors are present.
        """
        tree = self._to_tree(xml_source)
        root = copy.deepcopy(tree.getroot())
        tree = ET.ElementTree(root)

        if remove_existing_ev:
            self.instance_modifier.remove_existing_exceptional_values(root)

        errors = list(self._schema_errors(tree, xml_source))
        structural = [e for e in errors if self.error_mapper.is_structural_error(e)]
        if structural:
            raise SDC4StructuralValidationError(structural)

        result = RecoveryResult(tree=tree)
        covered: Dict[int, Recovery] = {}
        for error in errors:
            ev_type = self.error_mapper.map_error(error)
            reason = " ".join((error.reason or error.message or "").split())
            target = self.instance_modifier._find_element_by_xpath(root, error.path) if error.path else None
            parent = self.instance_modifier._find_parent_element(root, target) if target is not None else None
            if ev_type is None or parent is None:
                result.unrecoverable.append(error)
                continue
            if id(parent) in covered:          # a second failure in a value already covered
                continue
            existing = next((c for c in parent if isinstance(c.tag, str)
                             and c.tag.rsplit("}", 1)[-1] in EXCEPTIONAL_VALUE_CODES), None)
            if existing is not None:
                code = existing.tag.rsplit("}", 1)[-1]
                rec = Recovery(path=error.path, code=code, name=ExceptionalValueType.from_code(code).ev_name,
                               reason=reason, inserted=False)
            elif self.instance_modifier.insert_exceptional_value(
                    root=root, xpath=error.path, ev_type=ev_type, reason=error.reason):
                rec = Recovery(path=error.path, code=ev_type.code, name=ev_type.ev_name, reason=reason, inserted=True)
            else:
                result.unrecoverable.append(error)
                continue
            covered[id(parent)] = rec
            result.recoveries.append(rec)
        return result

    def validate_with_recovery(
        self,
        xml_source: Union[str, Path, ET.Element, XMLResource],
        output_path: Optional[Union[str, Path]] = None,
        remove_existing_ev: bool = False,
        save: bool = True,
    ) -> ET.ElementTree:
        """
        Validate an XML instance and insert ExceptionalValue elements for errors.

        Tier 1 (structural) errors cause a hard reject (SDC4StructuralValidationError).
        Tier 2 (semantic) errors are quarantined with ExceptionalValue tags (see
        `recover()`, which also returns what was covered and why). An error that
        cannot be covered raises SDC4UnrecoverableError rather than returning a
        record with an invalid value nobody marked (4.6.0).

        The recovered XML is saved unless save=False. When saving and no
        output_path is given, defaults to '{stem}-ev{suffix}' beside the input.

        Returns:
            Modified XML ElementTree with ExceptionalValue elements inserted.

        Raises:
            SDC4StructuralValidationError: If structural (Tier 1) errors are present.
            SDC4UnrecoverableError: If a semantic error cannot be covered.
            ValueError: If save=True but output_path cannot be determined.
        """
        original_file_path = Path(xml_source) if isinstance(xml_source, (str, Path)) else None
        result = self.recover(xml_source, remove_existing_ev=remove_existing_ev)
        if result.unrecoverable:
            raise SDC4UnrecoverableError(result.unrecoverable)
        tree = result.tree

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
        remove_existing_ev: bool = False,
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
