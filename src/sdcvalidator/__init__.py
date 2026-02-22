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
sdcvalidator — SDC4 structural validator.

Thin wrapper over xmlschema with two-tier error classification.
"""

__version__ = "4.1.0"

from .validator import SDC4Validator, ValidationResult
from .error_classifier import ErrorClassifier
from .constants import ErrorTier
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
    "ErrorTier",
    "validate_sdc4_schema_compliance",
    "assert_sdc4_schema_compliance",
    "SDC4SchemaValidationError",
]
