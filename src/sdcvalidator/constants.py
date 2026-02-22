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
Constants and type definitions for SDC4 validation.
"""

from enum import Enum

# SDC4 Namespace URIs
SDC4_NAMESPACE = "https://semanticdatacharter.com/ns/sdc4/"
SDC4_META_NAMESPACE = "https://semanticdatacharter.com/ontology/sdc4-meta/"
XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"


class ErrorTier(Enum):
    """
    Two-tier error classification for SDC4 validation.

    STRUCTURAL (Tier 1): Unknown elements, wrong nesting, cardinality -> REJECT
    SEMANTIC (Tier 2): Type errors, pattern violations, range constraints -> REPORT
    """
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"


# Data-bearing elements in SDC4 schemas
DATA_BEARING_ELEMENTS = {
    'xdstring-value',
    'xdcount-value',
    'xdquantity-value',
    'xdboolean-value',
    'xdfile-value',
    'xdlink-value',
    'xdtemporal-value',
    'xdordinal-value',
    'xdratio-value',
    'xdinterval-value',
    'xdtoken-value',
}

# Structural/metadata elements that should FAIL validation (not recoverable)
STRUCTURAL_ELEMENTS = {
    'label',           # Component labels
    'act',             # Audit/control/trust
    'vtb',             # Valid time begin
    'vte',             # Valid time end
    'tr',              # Transaction time
    'modified',        # Modification timestamp
    'latitude',        # Geographic coordinate
    'longitude',       # Geographic coordinate
    'normal-status',   # Quantified metadata
    'magnitude-status',  # Quantified metadata
    'accuracy_margin',   # Quantified metadata
    'precision_digits',  # Quantified metadata
}
