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
Unit tests for the SDC4 instance modifier.
"""

from xml.etree import ElementTree as ET

from sdcvalidator import InstanceModifier, ExceptionalValueType
from sdcvalidator.constants import SDC4_NAMESPACE


class TestInstanceModifier:

    def setup_method(self):
        self.modifier = InstanceModifier()

    def test_extract_element_name_simple(self):
        assert self.modifier._extract_element_name_from_xpath('/root/xdstring-value') == 'xdstring-value'

    def test_extract_element_name_with_namespace(self):
        assert self.modifier._extract_element_name_from_xpath('/sdc4:root/sdc4:xdcount-value') == 'xdcount-value'

    def test_extract_element_name_with_predicate(self):
        assert self.modifier._extract_element_name_from_xpath('/root/xdstring-value[1]') == 'xdstring-value'

    def test_extract_element_name_empty(self):
        assert self.modifier._extract_element_name_from_xpath('') is None
        assert self.modifier._extract_element_name_from_xpath(None) is None

    def test_create_exceptional_value_element(self):
        ev_elem = self.modifier._create_exceptional_value_element(ExceptionalValueType.INV)
        assert ev_elem.tag == f'{{{SDC4_NAMESPACE}}}INV'
        ev_name = ev_elem.find('ev-name')
        assert ev_name is not None
        assert ev_name.text == 'Invalid'

    def test_create_exceptional_value_element_with_reason(self):
        ev_elem = self.modifier._create_exceptional_value_element(
            ExceptionalValueType.NI, reason="test reason"
        )
        assert ev_elem.tag == f'{{{SDC4_NAMESPACE}}}NI'

    def test_remove_existing_exceptional_values(self):
        root = ET.fromstring(f'''
        <root xmlns:sdc4="{SDC4_NAMESPACE}">
            <label>Test</label>
            <sdc4:INV><ev-name>Invalid</ev-name></sdc4:INV>
            <xdstring-value>data</xdstring-value>
        </root>
        ''')
        self.modifier.remove_existing_exceptional_values(root)
        # INV element should be removed
        for child in root:
            local = child.tag.split('}')[1] if '}' in child.tag else child.tag
            assert local != 'INV'

    def test_structural_element_not_tagged(self):
        """A structural element (label) must not receive an ExceptionalValue."""
        root = ET.fromstring(f'''
        <root xmlns:sdc4="{SDC4_NAMESPACE}">
            <label>Test</label>
        </root>
        ''')
        ok = self.modifier.insert_exceptional_value(
            root, '/root/label', ExceptionalValueType.INV
        )
        assert ok is False
