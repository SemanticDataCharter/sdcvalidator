"""
ExceptionalValue mapping by the constraint that failed (4.6.3).

Before 4.6.3 the mapper matched xmlschema's English messages, and when xmlschema's wording changed,
every facet violation fell through to NI. These tests fix the mapping to the constraint itself.
"""
import pytest
import xmlschema

from sdcvalidator.error_mapper import ErrorMapper

XSD = '''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xs:element name="r"><xs:complexType><xs:sequence>
 <xs:element name="maxlen-value"><xs:simpleType><xs:restriction base="xs:string"><xs:maxLength value="3"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="minlen-value"><xs:simpleType><xs:restriction base="xs:string"><xs:minLength value="3"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="maxinc-value"><xs:simpleType><xs:restriction base="xs:decimal"><xs:maxInclusive value="3"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="minexc-value"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minExclusive value="3"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="totdig-value"><xs:simpleType><xs:restriction base="xs:decimal"><xs:totalDigits value="2"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="pattern-value"><xs:simpleType><xs:restriction base="xs:string"><xs:pattern value="[a-z]+"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="enum-value"><xs:simpleType><xs:restriction base="xs:string"><xs:enumeration value="ab"/></xs:restriction></xs:simpleType></xs:element>
 <xs:element name="fixed-value" type="xs:string" fixed="abc"/>
 <xs:element name="nni-value" type="xs:nonNegativeInteger"/>
 <xs:element name="lang-value" type="xs:language"/>
 <xs:element name="decimal-value" type="xs:decimal"/>
 <xs:element name="asserted"><xs:complexType><xs:sequence><xs:element name="a" type="xs:integer"/></xs:sequence><xs:assert test="a gt 5"/></xs:complexType></xs:element>
 <xs:element name="label" type="xs:integer"/>
</xs:sequence></xs:complexType></xs:element></xs:schema>'''

DOC = ('<r><maxlen-value>abcd</maxlen-value><minlen-value>ab</minlen-value><maxinc-value>4</maxinc-value>'
       '<minexc-value>3</minexc-value><totdig-value>123</totdig-value><pattern-value>AB</pattern-value>'
       '<enum-value>zz</enum-value><fixed-value>abd</fixed-value><nni-value>-1</nni-value>'
       '<lang-value>not a lang</lang-value><decimal-value>x</decimal-value><asserted><a>1</a></asserted>'
       '<label>x</label></r>')


@pytest.fixture(scope='module')
def mapped():
    schema = xmlschema.XMLSchema11(XSD)
    mapper = ErrorMapper()
    out = {}
    for error in schema.iter_errors(DOC):
        ev = mapper.map_error(error)
        out[error.path.rsplit('/', 1)[-1]] = ev.code if ev else None
    return out


@pytest.mark.parametrize('element, code', [
    ('maxlen-value', 'INV'),
    ('minlen-value', 'INV'),
    ('maxinc-value', 'INV'),
    ('minexc-value', 'INV'),
    ('totdig-value', 'INV'),
    ('pattern-value', 'INV'),
    ('enum-value', 'OTH'),
    ('fixed-value', 'INV'),
    ('nni-value', 'INV'),        # a built-in type's own range
    ('lang-value', 'INV'),       # a built-in type's own pattern
    ('decimal-value', 'INV'),    # not of its type at all
    ('asserted', 'INV'),
    ('label', None),             # a structural element is never tagged
])
def test_maps_by_constraint(mapped, element, code):
    assert mapped[element] == code
