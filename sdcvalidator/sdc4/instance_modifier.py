#
# Copyright (c), 2025, Axius-SDC, Inc.
# All rights reserved.
# This file is distributed under the terms of the MIT License.
#
"""
Modifies XML instance documents to insert SDC4 ExceptionalValue elements.
"""

from typing import Optional, Dict, Any
from xml.etree import ElementTree as ET
from .constants import (
    SDC4_NAMESPACE,
    ExceptionalValueType,
    EXCEPTIONAL_VALUE_INSERT_AFTER,
    EXCEPTIONAL_VALUE_INSERT_BEFORE,
    DATA_BEARING_ELEMENTS,
    STRUCTURAL_ELEMENTS
)


class InstanceModifier:
    """
    Modifies XML instance documents by inserting ExceptionalValue elements
    at validation error locations.

    Uses the SDC4 "quarantine-and-tag" pattern where invalid values are
    preserved and flagged with ExceptionalValue elements.
    """

    def __init__(self, namespace_prefix: str = 'sdc4'):
        """
        Initialize the instance modifier.

        :param namespace_prefix: The XML namespace prefix to use for SDC4 elements (default: 'sdc4').
        """
        self.namespace_prefix = namespace_prefix
        self.sdc4_ns = SDC4_NAMESPACE

    def insert_exceptional_value(self,
                                   root: ET.Element,
                                   xpath: str,
                                   ev_type: ExceptionalValueType,
                                   reason: Optional[str] = None) -> bool:
        """
        Insert an ExceptionalValue element at the specified XPath location.

        Only data-bearing elements (xdstring-value, xdcount-value, etc.) can receive
        ExceptionalValue tags. Structural/metadata elements (label, vtb, vte, tr, etc.)
        should not be tagged.

        :param root: The root element of the XML document.
        :param xpath: XPath to the element where the error occurred.
        :param ev_type: The ExceptionalValueType to insert.
        :param reason: Optional additional reason text.
        :return: True if insertion was successful, False if element should not be tagged.
        """
        # Check if this element should receive ExceptionalValue tag
        element_name = self._extract_element_name_from_xpath(xpath)

        # Don't tag structural elements - these should fail validation
        if element_name and element_name in STRUCTURAL_ELEMENTS:
            return False

        # All other elements (data-bearing, custom, or unknown) can be tagged
        # This allows flexibility for custom element names and future SDC versions

        # Ensure namespace is registered
        self._register_namespace()

        # Find the element with the invalid value using XPath
        invalid_elem = self._find_element_by_xpath(root, xpath)
        if invalid_elem is None:
            return False

        # Find the parent element (XdAnyType) where ExceptionalValue should be inserted
        parent_elem = self._find_parent_element(root, invalid_elem)
        if parent_elem is None:
            return False

        # Create the ExceptionalValue element
        ev_element = self._create_exceptional_value_element(ev_type, reason)

        # Insert at the appropriate position in the parent's sequence
        insert_pos = self._find_insertion_position(parent_elem)
        parent_elem.insert(insert_pos, ev_element)

        return True

    def _extract_element_name_from_xpath(self, xpath: str) -> Optional[str]:
        """
        Extract the element name from an XPath expression.

        :param xpath: The XPath expression.
        :return: The local element name (without namespace prefix), or None.
        """
        if not xpath:
            return None

        # Get the last path component
        parts = xpath.strip('/').split('/')
        if not parts:
            return None

        last_part = parts[-1]

        # Remove namespace prefix (e.g., 'sdc4:xdstring-value' -> 'xdstring-value')
        if ':' in last_part:
            last_part = last_part.split(':')[-1]

        # Remove predicates (e.g., 'xdstring-value[1]' -> 'xdstring-value')
        if '[' in last_part:
            last_part = last_part[:last_part.index('[')]

        return last_part if last_part else None

    def _register_namespace(self):
        """Register the SDC4 namespace with ElementTree."""
        try:
            ET.register_namespace(self.namespace_prefix, self.sdc4_ns)
        except Exception:
            # Namespace might already be registered
            pass

    def _find_element_by_xpath(self, root: ET.Element, xpath: str) -> Optional[ET.Element]:
        """
        Find an element by XPath (including Clark notation support).

        :param root: The root element to search from.
        :param xpath: The XPath expression (may use Clark notation: {namespace}localname).
        :return: The found element or None.
        """
        if not xpath:
            return None

        # Handle Clark notation in XPath by traversing manually
        # Clark notation: /{namespace}localname/{namespace}localname/...
        if '{' in xpath:
            return self._find_element_by_clark_path(root, xpath)

        # Handle namespace prefixes in XPath
        # Convert xpath like /ns:root/ns:child to proper namespaced search
        namespaces = self._extract_namespaces(root)

        try:
            # Try direct XPath first
            elements = root.findall(xpath, namespaces)
            if elements:
                return elements[0]

            # If that fails, try a simpler approach for direct paths
            # This handles cases where the error path is relative or simplified
            if xpath.startswith('/'):
                xpath = '.' + xpath

            elements = root.findall(xpath, namespaces)
            if elements:
                return elements[0]

        except Exception as e:
            # If XPath fails, try to parse it manually
            # This is a fallback for complex XPath expressions
            return self._find_element_by_manual_parse(root, xpath)

        return None

    def _find_element_by_clark_path(self, root: ET.Element, clark_path: str) -> Optional[ET.Element]:
        """
        Find an element by traversing a Clark notation path.

        Clark notation: /{namespace}localname/{namespace}localname/...

        :param root: The root element to search from.
        :param clark_path: The path using Clark notation.
        :return: The found element or None.
        """
        # Parse Clark notation path components
        # Need to be careful not to split on slashes inside the namespace URI
        parts = []
        i = 0
        while i < len(clark_path):
            if clark_path[i] == '/':
                # Skip slashes
                i += 1
                continue
            elif clark_path[i] == '{':
                # Start of namespaced element: {namespace}localname
                # Find the matching '}'
                end_brace = clark_path.index('}', i)
                # Find the next '/' or end of string
                next_slash = clark_path.find('/', end_brace)
                if next_slash == -1:
                    next_slash = len(clark_path)
                # Extract the full element name with namespace
                part = clark_path[i:next_slash]
                parts.append(part)
                i = next_slash
            else:
                # Element without namespace
                next_slash = clark_path.find('/', i)
                if next_slash == -1:
                    next_slash = len(clark_path)
                part = clark_path[i:next_slash]
                parts.append(part)
                i = next_slash

        if not parts:
            return None

        # Start from root
        current = root

        # Check if the first part is the root element itself
        if parts[0] == root.tag:
            # Skip the root element in the path
            parts = parts[1:]
            if not parts:
                return root

        # Traverse each part of the path
        for part in parts:
            # The part is in Clark notation: {namespace}localname or just localname
            found = False
            for child in current:
                if child.tag == part:
                    current = child
                    found = True
                    break

            if not found:
                return None

        return current

    def _find_parent_element(self, root: ET.Element, child: ET.Element) -> Optional[ET.Element]:
        """
        Find the parent element of a given child element.

        :param root: The root element to search from.
        :param child: The child element whose parent we want to find.
        :return: The parent element or None.
        """
        # Iterate through all elements in the tree
        for parent in root.iter():
            if child in list(parent):
                return parent
        return None

    def _extract_namespaces(self, root: ET.Element) -> Dict[str, str]:
        """
        Extract namespace mappings from the root element.

        :param root: The root element.
        :return: Dictionary of namespace prefix to URI mappings.
        """
        namespaces = {}

        # Get namespace map from root
        for prefix, uri in root.attrib.items():
            if prefix.startswith('{http://www.w3.org/2000/xmlns/}'):
                prefix_name = prefix.split('}')[1]
                namespaces[prefix_name] = uri
            elif prefix == 'xmlns':
                namespaces[''] = root.attrib[prefix]

        # Walk through the tree to find all namespace declarations
        for elem in root.iter():
            tag = elem.tag
            if tag.startswith('{'):
                ns_uri = tag[1:tag.index('}')]
                # Try to find or assign a prefix for this namespace
                if ns_uri not in namespaces.values():
                    # Look for existing prefix in attribs
                    for key, value in elem.attrib.items():
                        if key.startswith('{http://www.w3.org/2000/xmlns/}'):
                            prefix_name = key.split('}')[1]
                            if value == ns_uri:
                                namespaces[prefix_name] = ns_uri
                                break

        # Ensure sdc4 namespace is included
        if SDC4_NAMESPACE not in namespaces.values():
            namespaces[self.namespace_prefix] = SDC4_NAMESPACE

        return namespaces

    def _find_element_by_manual_parse(self, root: ET.Element, xpath: str) -> Optional[ET.Element]:
        """
        Manually parse XPath for simple cases when ElementTree XPath fails.

        :param root: The root element.
        :param xpath: The XPath expression.
        :return: The found element or None.
        """
        # This is a simplified XPath parser for basic paths like /root/child[1]/grandchild
        # For more complex XPath, this should be enhanced or use a proper XPath library

        parts = xpath.strip('/').split('/')
        current = root

        for part in parts:
            # Handle indexed access like element[1]
            if '[' in part and ']' in part:
                elem_name = part[:part.index('[')]
                index_str = part[part.index('[') + 1:part.index(']')]
                try:
                    index = int(index_str) - 1  # XPath is 1-indexed
                except ValueError:
                    # Complex predicate, skip for now
                    return None

                children = [child for child in current if self._local_name(child.tag) == elem_name]
                if index < len(children):
                    current = children[index]
                else:
                    return None
            else:
                # Simple element name
                found = False
                for child in current:
                    if self._local_name(child.tag) == part:
                        current = child
                        found = True
                        break
                if not found:
                    return None

        return current

    def _local_name(self, tag: str) -> str:
        """Extract the local name from a namespaced tag."""
        if tag.startswith('{'):
            return tag[tag.index('}') + 1:]
        return tag

    def _create_exceptional_value_element(self,
                                           ev_type: ExceptionalValueType,
                                           reason: Optional[str] = None) -> ET.Element:
        """
        Create an ExceptionalValue element.

        Per SDC4 spec, the element name is the ExceptionalValue code (INV, UNK, etc.)
        with a child <ev-name> element containing the human-readable name.

        Example:
            <sdc4:INV>
                <ev-name>Invalid</ev-name>
            </sdc4:INV>

        :param ev_type: The ExceptionalValueType.
        :param reason: Optional additional reason text.
        :return: The created element.
        """
        # Create element with the ExceptionalValue code as the tag name
        tag = f"{{{self.sdc4_ns}}}{ev_type.code}"
        ev_elem = ET.Element(tag)

        # Add the ev-name child element
        ev_name_elem = ET.SubElement(ev_elem, "ev-name")
        ev_name_elem.text = ev_type.ev_name

        # Optionally add reason as a comment
        if reason:
            comment = ET.Comment(f" Validation error: {reason} ")
            ev_elem.insert(0, comment)

        return ev_elem

    def _find_insertion_position(self, parent: ET.Element) -> int:
        """
        Find the correct position to insert the ExceptionalValue element.

        Per SDC4 schema, ExceptionalValue should come after 'label' and 'act',
        but before 'vtb', 'vte', 'tr', 'modified', etc.

        :param parent: The parent element.
        :return: The index position to insert at.
        """
        # Find the last occurrence of elements that should come before ExceptionalValue
        insert_pos = 0

        for i, child in enumerate(parent):
            local_name = self._local_name(child.tag)

            # Skip existing ExceptionalValue elements
            if local_name in ['INV', 'OTH', 'UNC', 'NI', 'NA', 'UNK', 'ASKU', 'ASKR',
                              'NASK', 'NAV', 'MSK', 'DER', 'PINF', 'NINF', 'TRC', 'QS']:
                continue

            # Check if this element should come before ExceptionalValue
            if local_name in EXCEPTIONAL_VALUE_INSERT_AFTER:
                insert_pos = i + 1
            elif local_name in EXCEPTIONAL_VALUE_INSERT_BEFORE:
                # Stop here - don't go past elements that should come after
                break
            elif local_name.endswith('-value') or local_name.endswith('-units'):
                # These are the value elements, ExceptionalValue should come before them
                break

        return insert_pos

    def remove_existing_exceptional_values(self, root: ET.Element):
        """
        Remove any existing ExceptionalValue elements from the document.

        :param root: The root element of the XML document.
        """
        ev_codes = ['INV', 'OTH', 'UNC', 'NI', 'NA', 'UNK', 'ASKU', 'ASKR',
                    'NASK', 'NAV', 'MSK', 'DER', 'PINF', 'NINF', 'TRC', 'QS']

        for elem in root.iter():
            for child in list(elem):
                local_name = self._local_name(child.tag)
                if local_name in ev_codes:
                    elem.remove(child)
