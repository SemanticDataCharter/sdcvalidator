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
XSD 1.1 substitution-group restriction support.

SDC4 data models restrict a content model that references an abstract
substitution-group head (``sdc4:Item``) down to the specific member elements a
model defines. For example the reference-model cluster content ``label?, Item*``
is restricted to ``label?, ms-A?, ms-B?, ...`` where each ``ms-*`` is a member
of ``Item``'s substitution group.

This is a valid restriction under **XSD 1.1 Part 1, Section 3.4.6.4 "Content type
restricts (Complex Content)"**, which defines restriction in terms of the
instances a content model accepts. XSD 1.1 removed the XSD 1.0 particle
name-matching rule (``NameAndTypeOK``). A conformant XSD 1.1 processor accepts
the construct, and the Apache Xerces-J XML Schema 1.1 reference build does accept
it. See ``SDCRM/docs/VALIDATORS.md`` and
https://www.w3.org/TR/xmlschema11-1/#derivation-ok-restriction .

``xmlschema`` (through at least 4.x) still applies the removed XSD 1.0 rule and
rejects this construct at schema-build time with "the derived group is an illegal
restriction". This module recognises that specific false positive, structurally,
so the schema can be built while genuinely invalid restrictions stay fatal.

Recognition is not message-matching alone: for the reported complex type we
confirm that every element in the derived content model either matches a base
element by name (an ordinary restriction xmlschema already checks) or is a member
of a substitution group whose head appears in the base content model, with
compatible occurrences. A restriction to a non-member element, or one that widens
occurrences, is not recognised and remains a fatal error.
"""

from typing import Union
from pathlib import Path

from xmlschema import XMLSchema11
from xmlschema.validators.exceptions import XMLSchemaParseError

# xmlschema phrasings for the complex-content restriction rejection.
_RESTRICTION_MARKERS = ("illegal restriction", "not a valid restriction")


def _occurs_within(member, head) -> bool:
    """True if ``member``'s occurrence range is inside ``head``'s range, i.e. the
    member is a valid occurrence-restriction of the head particle."""
    if member.min_occurs < head.min_occurs:
        return False
    if head.max_occurs is None:  # head is unbounded, any bound is within it
        return True
    if member.max_occurs is None:
        return False
    return member.max_occurs <= head.max_occurs


def is_substitution_group_restriction_false_positive(error) -> bool:
    """Return True iff ``error`` is xmlschema wrongly rejecting a valid XSD 1.1
    substitution-group-member restriction (Section 3.4.6.4).

    Narrow by construction: returns False for genuinely invalid restrictions
    (restricting to a non-member element, or widening an element's occurrences),
    so it never masks a real schema defect.
    """
    if not isinstance(error, XMLSchemaParseError):
        return False
    message = (getattr(error, "message", "") or "").lower()
    if not any(marker in message for marker in _RESTRICTION_MARKERS):
        return False

    complex_type = getattr(error, "validator", None)
    base_type = getattr(complex_type, "base_type", None)
    derived_group = getattr(complex_type, "content", None)
    base_group = getattr(base_type, "content", None)
    if complex_type is None or base_type is None:
        return False
    if derived_group is None or base_group is None:
        return False

    try:
        # Only the element-only sequence-restricts-sequence case is in scope.
        if getattr(derived_group, "model", None) != "sequence":
            return False
        if getattr(base_group, "model", None) != "sequence":
            return False

        substitution_groups = complex_type.maps.substitution_groups

        base_named = {}   # name -> base element declaration
        base_heads = []   # substitution-group head particles in the base
        for particle in base_group.iter_model():
            name = getattr(particle, "name", None)
            if name is None:
                return False  # a wildcard or nested group in the base — out of scope
            base_named[name] = particle
            # An element heads a substitution group when its name keys the map.
            # The head need not be abstract (S3Model's 'Items' head is not).
            if name in substitution_groups:
                base_heads.append(particle)

        for derived in derived_group.iter_model():
            dname = getattr(derived, "name", None)
            if dname is None:
                return False  # wildcard/nested group in the restriction — out of scope

            if dname in base_named:
                # Ordinary same-name restriction; xmlschema's own element check
                # decides whether it is valid (occurrence tightening, fixed value,
                # validly-derived type). If it is not, this is a real error.
                if not derived.is_restriction(base_named[dname]):
                    return False
                continue

            # Not a same-name element: it must substitute for a base head element
            # and its occurrences must fall inside that head's occurrences.
            matched = False
            for head in base_heads:
                members = substitution_groups.get(head.name) or ()
                if any(getattr(m, "name", None) == dname for m in members):
                    matched = _occurs_within(derived, head)
                    break
            if not matched:
                return False

        return True
    except Exception:
        # Any unexpected shape: be conservative and treat as a real error.
        return False


def build_xsd11_schema(
    source: Union[str, Path, "XMLSchema11"], validation: str = "strict", **kwargs
) -> XMLSchema11:
    """Build an ``XMLSchema11`` while tolerating only the known-valid XSD 1.1
    substitution-group restriction that xmlschema false-rejects.

    A drop-in for the ``XMLSchema11(source, validation=..., **kwargs)`` constructor:
    extra keyword arguments (``uri_mapper``, ``base_url``, ``locations``, ...) are
    forwarded unchanged to ``XMLSchema11``.

    Strict mode is preserved for every other case: a clean schema builds once in
    strict mode; a schema that fails strict only because of the substitution-group
    false positive is rebuilt in lax mode and returned; any genuine error keeps
    the build fatal. ``lax`` and ``skip`` are passed through unchanged.

    A lax-built schema still enforces the restriction during instance validation
    (valid members are accepted, non-members rejected); only xmlschema's incorrect
    build-time check is bypassed.
    """
    if validation != "strict":
        return XMLSchema11(source, validation=validation, **kwargs)

    try:
        return XMLSchema11(source, validation="strict", **kwargs)
    except XMLSchemaParseError as strict_error:
        if not is_substitution_group_restriction_false_positive(strict_error):
            raise
        schema = XMLSchema11(source, validation="lax", **kwargs)
        genuine = [
            e for e in schema.all_errors
            if not is_substitution_group_restriction_false_positive(e)
        ]
        if genuine:
            # Real problems remain; surface the first one, not the false positive.
            raise genuine[0]
        return schema
