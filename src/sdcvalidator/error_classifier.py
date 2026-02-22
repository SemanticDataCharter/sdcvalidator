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
Classifies XML Schema validation errors into structural vs semantic tiers.
"""

import re
from typing import Optional, Dict, List
from xmlschema.validators.exceptions import (
    XMLSchemaValidationError,
    XMLSchemaDecodeError,
    XMLSchemaChildrenValidationError
)
from .constants import ErrorTier, STRUCTURAL_ELEMENTS


class ErrorClassifier:
    """
    Classifies XMLSchema validation errors into structural (Tier 1)
    vs semantic (Tier 2) categories.

    Structural errors (Tier 1) should cause immediate rejection:
    - Unknown/unexpected elements
    - Incomplete content (missing required children)
    - Cardinality violations (minOccurs/maxOccurs)

    Semantic errors (Tier 2) are reportable but not fatal:
    - Type conversion errors
    - Pattern violations
    - Enumeration violations
    - Range constraint violations
    """

    def classify(self, error: XMLSchemaValidationError) -> ErrorTier:
        """
        Classify a single validation error as structural or semantic.

        Args:
            error: The XML Schema validation error.

        Returns:
            ErrorTier.STRUCTURAL or ErrorTier.SEMANTIC
        """
        if self.is_structural_error(error):
            return ErrorTier.STRUCTURAL
        return ErrorTier.SEMANTIC

    def classify_all(
        self, errors: List[XMLSchemaValidationError]
    ) -> Dict[str, List[XMLSchemaValidationError]]:
        """
        Classify a list of errors into structural and semantic buckets.

        Args:
            errors: List of XML Schema validation errors.

        Returns:
            Dictionary with 'structural' and 'semantic' keys mapping
            to lists of errors.
        """
        result: Dict[str, List[XMLSchemaValidationError]] = {
            "structural": [],
            "semantic": [],
        }
        for error in errors:
            tier = self.classify(error)
            result[tier.value].append(error)
        return result

    def is_structural_error(self, error: XMLSchemaValidationError) -> bool:
        """
        Determine if an error is structural (Tier 1).

        Args:
            error: The validation error to classify.

        Returns:
            True if structural (reject), False if semantic (report).
        """
        # XMLSchemaChildrenValidationError — structural by nature
        if isinstance(error, XMLSchemaChildrenValidationError):
            # Unknown/unexpected element
            if error.invalid_tag is not None:
                return True
            # Check for incomplete content or cardinality issues
            if error.reason:
                reason_lower = error.reason.lower()
                if 'not complete' in reason_lower:
                    return True
                if 'occurs' in reason_lower and (
                    'minimum' in reason_lower or 'maximum' in reason_lower
                ):
                    return True

        # Check reason patterns for structural issues
        if error.reason:
            reason_lower = error.reason.lower()
            structural_patterns = [
                'unexpected child',
                'element not allowed',
                'not permitted here',
                'unknown element',
                'invalid child',
            ]
            if any(pattern in reason_lower for pattern in structural_patterns):
                return True

        # Everything else is semantic
        return False

    def _extract_element_name(self, xpath: Optional[str]) -> Optional[str]:
        """
        Extract the element name from an XPath expression.

        Handles paths like:
        - /DataModel/xdstring-value
        - /ns:DataModel/ns:xdstring-value[1]
        """
        if not xpath:
            return None

        parts = xpath.strip('/').split('/')
        if not parts:
            return None

        last_part = parts[-1]

        # Remove namespace prefix
        if ':' in last_part:
            last_part = last_part.split(':')[-1]

        # Remove predicates
        if '[' in last_part:
            last_part = last_part[:last_part.index('[')]

        return last_part if last_part else None

    def get_error_summary(self, error: XMLSchemaValidationError) -> Dict[str, str]:
        """
        Generate a summary of the classified error.

        Args:
            error: The validation error.

        Returns:
            A dictionary with error details.
        """
        tier = self.classify(error)
        return {
            'xpath': error.path or 'unknown',
            'error_type': type(error).__name__,
            'reason': error.reason or 'No reason provided',
            'tier': tier.value,
        }
