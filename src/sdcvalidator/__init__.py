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
sdcvalidator — SDC4 structural validator with ExceptionalValue recovery.

Thin wrapper over xmlschema with two-tier error classification and the SDC4
"quarantine-and-tag" recovery pattern (ISO 21090 ExceptionalValues).
"""

__version__ = "4.3.0"

# etree_tostring is re-exported from xmlschema so callers can serialize the
# ElementTree returned by validate_with_recovery() without importing xmlschema
# directly. The import location moved across xmlschema versions; try both.
try:  # xmlschema >= 2.x
    from xmlschema import etree_tostring
except ImportError:  # pragma: no cover - fallback for older layouts
    from xmlschema.etree import etree_tostring

from .validator import (
    SDC4Validator,
    ValidationResult,
    validate_with_recovery,
)
from .error_classifier import ErrorClassifier
from .error_mapper import ErrorMapper
from .instance_modifier import InstanceModifier
from .exceptions import SDC4StructuralValidationError
from .constants import (
    ErrorTier,
    ExceptionalValueType,
    EXCEPTIONAL_VALUE_TYPES,
)
from .schema_checker import (
    validate_sdc4_schema_compliance,
    assert_sdc4_schema_compliance,
    SDC4SchemaValidationError,
)

# Intentionally NOT exporting XMLSchema11 — SDCStudio's fallback import handles this.

__all__ = [
    "__version__",
    "SDC4Validator",
    "ValidationResult",
    "ErrorClassifier",
    "ErrorMapper",
    "InstanceModifier",
    "ErrorTier",
    "ExceptionalValueType",
    "EXCEPTIONAL_VALUE_TYPES",
    "SDC4StructuralValidationError",
    "validate_with_recovery",
    "etree_tostring",
    "validate_sdc4_schema_compliance",
    "assert_sdc4_schema_compliance",
    "SDC4SchemaValidationError",
]
