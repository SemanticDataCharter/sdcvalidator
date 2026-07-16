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
Tests for XSD 1.1 substitution-group restriction support.

The reference behaviour is the Apache Xerces-J XML Schema 1.1 build, which
accepts a Data Model that restricts an abstract substitution-group head to
specific member elements (valid per XSD 1.1 Part 1 Section 3.4.6.4) and rejects
genuinely invalid restrictions. build_xsd11_schema must match that: accept the
valid construct that stock xmlschema false-rejects, keep real errors fatal, and
still enforce the restriction during instance validation.
"""

import pytest
from xmlschema.validators.exceptions import XMLSchemaParseError

from sdcvalidator.xsd11_restriction import (
    build_xsd11_schema,
    is_substitution_group_restriction_false_positive,
)


# A reference model with an ABSTRACT substitution-group head (like sdc4:Item),
# concrete member types that reach the head's type through an extension (like
# ClusterType/XdAdapterType extending ItemType), and a cluster whose content is
# `label?, Item*`.
ABSTRACT_HEAD_RM = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning"
            xmlns:t="urn:test" targetNamespace="urn:test"
            elementFormDefault="qualified" vc:minVersion="1.1">
  <xsd:complexType abstract="true" name="ItemType"><xsd:sequence/></xsd:complexType>
  <xsd:element abstract="true" name="Item" type="t:ItemType"/>
  <xsd:complexType name="MidType"><xsd:complexContent><xsd:extension base="t:ItemType">
     <xsd:sequence><xsd:element name="v" type="xsd:string" minOccurs="0"/></xsd:sequence>
  </xsd:extension></xsd:complexContent></xsd:complexType>
  <xsd:complexType name="MemberType"><xsd:complexContent><xsd:restriction base="t:MidType">
     <xsd:sequence><xsd:element name="v" type="xsd:string" minOccurs="0"/></xsd:sequence>
  </xsd:restriction></xsd:complexContent></xsd:complexType>
  <xsd:element name="ms-a" substitutionGroup="t:Item" type="t:MemberType"/>
  <xsd:element name="ms-b" substitutionGroup="t:Item" type="t:MemberType"/>
  <xsd:complexType name="ClusterType"><xsd:complexContent><xsd:extension base="t:ItemType">
    <xsd:sequence>
      <xsd:element name="label" type="xsd:string" minOccurs="0"/>
      <xsd:element ref="t:Item" minOccurs="0" maxOccurs="unbounded"/>
    </xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>
  {derived}
  <xsd:element name="root" type="t:DataCluster"/>
</xsd:schema>
"""

# The valid restriction that stock xmlschema false-rejects: a fixed-value leading
# label plus specific substitution-group members in place of the Item head.
VALID_DERIVED = """
  <xsd:complexType name="DataCluster"><xsd:complexContent><xsd:restriction base="t:ClusterType">
    <xsd:sequence>
      <xsd:element name="label" type="xsd:string" minOccurs="1" maxOccurs="1" fixed="Fixed Label"/>
      <xsd:element ref="t:ms-a" minOccurs="0" maxOccurs="1"/>
      <xsd:element ref="t:ms-b" minOccurs="0" maxOccurs="1"/>
    </xsd:sequence></xsd:restriction></xsd:complexContent></xsd:complexType>
"""

# Genuinely invalid: restrict a required head slot to an element that is NOT a
# member of the head's substitution group. xmlschema raises "illegal restriction"
# here, and the recognizer must decline to suppress it (stranger is not a member),
# so the error stays fatal.
INVALID_NONMEMBER_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning"
            xmlns:t="urn:test" targetNamespace="urn:test"
            elementFormDefault="qualified" vc:minVersion="1.1">
  <xsd:complexType abstract="true" name="ItemType"><xsd:sequence/></xsd:complexType>
  <xsd:element abstract="true" name="Item" type="t:ItemType"/>
  <xsd:complexType name="MemberType"><xsd:complexContent><xsd:restriction base="t:ItemType">
     <xsd:sequence/></xsd:restriction></xsd:complexContent></xsd:complexType>
  <xsd:element name="ms-a" substitutionGroup="t:Item" type="t:MemberType"/>
  <!-- stranger is derived from ItemType but is NOT in Item's substitution group -->
  <xsd:element name="stranger" type="t:MemberType"/>
  <xsd:complexType name="BaseType"><xsd:sequence>
    <xsd:element ref="t:Item" minOccurs="1" maxOccurs="1"/>
  </xsd:sequence></xsd:complexType>
  <xsd:complexType name="DataCluster"><xsd:complexContent><xsd:restriction base="t:BaseType">
    <xsd:sequence>
      <xsd:element ref="t:stranger" minOccurs="1" maxOccurs="1"/>
    </xsd:sequence></xsd:restriction></xsd:complexContent></xsd:complexType>
  <xsd:element name="root" type="t:DataCluster"/>
</xsd:schema>
"""

# A reference model whose substitution-group head element is NOT abstract (like
# S3Model's 'Items'); only its type is abstract.
NONABSTRACT_HEAD_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning"
            xmlns:t="urn:test" targetNamespace="urn:test"
            elementFormDefault="qualified" vc:minVersion="1.1">
  <xsd:complexType abstract="true" name="ItemsType"><xsd:sequence/></xsd:complexType>
  <xsd:element name="Items" type="t:ItemsType"/>
  <xsd:complexType name="MemberType"><xsd:complexContent><xsd:restriction base="t:ItemsType">
     <xsd:sequence/></xsd:restriction></xsd:complexContent></xsd:complexType>
  <xsd:element name="ms-a" substitutionGroup="t:Items" type="t:MemberType"/>
  <xsd:element name="ms-b" substitutionGroup="t:Items" type="t:MemberType"/>
  <xsd:complexType name="ClusterType"><xsd:sequence>
    <xsd:element name="label" type="xsd:string" minOccurs="0"/>
    <xsd:element ref="t:Items" minOccurs="0" maxOccurs="unbounded"/>
  </xsd:sequence></xsd:complexType>
  <xsd:complexType name="DataCluster"><xsd:complexContent><xsd:restriction base="t:ClusterType">
    <xsd:sequence>
      <xsd:element name="label" type="xsd:string" minOccurs="1" maxOccurs="1" fixed="X"/>
      <xsd:element ref="t:ms-a" minOccurs="0" maxOccurs="1"/>
      <xsd:element ref="t:ms-b" minOccurs="0" maxOccurs="1"/>
    </xsd:sequence></xsd:restriction></xsd:complexContent></xsd:complexType>
  <xsd:element name="root" type="t:DataCluster"/>
</xsd:schema>
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def test_valid_substitution_restriction_builds(tmp_path):
    """The valid substitution-group restriction that stock xmlschema rejects
    must build under strict validation."""
    path = _write(tmp_path, "valid.xsd", ABSTRACT_HEAD_RM.format(derived=VALID_DERIVED))
    schema = build_xsd11_schema(path)  # strict by default
    assert "root" in schema.elements


def test_nonabstract_head_builds(tmp_path):
    """A substitution-group head that is not declared abstract (S3Model 'Items'
    style) is still recognised."""
    path = _write(tmp_path, "s3m.xsd", NONABSTRACT_HEAD_SCHEMA)
    schema = build_xsd11_schema(path)
    assert "root" in schema.elements


def test_valid_restriction_enforced_on_instances(tmp_path):
    """A lax-built schema must still enforce the restriction: valid members are
    accepted, non-members rejected."""
    path = _write(tmp_path, "valid.xsd", ABSTRACT_HEAD_RM.format(derived=VALID_DERIVED))
    schema = build_xsd11_schema(path)
    schema.validate('<root xmlns="urn:test"><label>Fixed Label</label><ms-a/></root>')
    with pytest.raises(Exception):
        schema.validate('<root xmlns="urn:test"><label>Fixed Label</label><intruder/></root>')


def test_nonmember_restriction_stays_fatal(tmp_path):
    """Restricting the head slot to a non-member element is a real error and must
    remain fatal."""
    path = _write(tmp_path, "nonmember.xsd", INVALID_NONMEMBER_SCHEMA)
    with pytest.raises(XMLSchemaParseError):
        build_xsd11_schema(path)


def test_widened_cardinality_stays_fatal(tmp_path):
    """Widening an element's occurrences is not a valid restriction and must
    remain fatal."""
    schema_xsd = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning"
            xmlns:t="urn:test" targetNamespace="urn:test" vc:minVersion="1.1">
  <xsd:complexType name="BaseType"><xsd:sequence>
    <xsd:element name="a" type="xsd:string" minOccurs="0" maxOccurs="1"/>
  </xsd:sequence></xsd:complexType>
  <xsd:complexType name="DerivedType"><xsd:complexContent>
    <xsd:restriction base="t:BaseType"><xsd:sequence>
      <xsd:element name="a" type="xsd:string" minOccurs="0" maxOccurs="3"/>
    </xsd:sequence></xsd:restriction></xsd:complexContent></xsd:complexType>
  <xsd:element name="root" type="t:DerivedType"/>
</xsd:schema>
"""
    path = _write(tmp_path, "widen.xsd", schema_xsd)
    with pytest.raises(XMLSchemaParseError):
        build_xsd11_schema(path)


def test_clean_schema_unaffected(tmp_path):
    """A schema with no restriction issues builds normally."""
    schema_xsd = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:t="urn:test" targetNamespace="urn:test">
  <xsd:element name="root" type="xsd:string"/>
</xsd:schema>
"""
    path = _write(tmp_path, "clean.xsd", schema_xsd)
    schema = build_xsd11_schema(path)
    assert "root" in schema.elements


def test_recognizer_ignores_non_restriction_errors():
    """The recognizer must not treat an unrelated error as the false positive."""
    class Other(Exception):
        message = "something else entirely"
    assert is_substitution_group_restriction_false_positive(Other()) is False
