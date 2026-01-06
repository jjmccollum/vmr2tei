#!/usr/bin/env python3

from typing import List
from lxml import etree as et # for reading TEI XML inputs

from .common import *


class Reading:
    """Base class for storing TEI XML reading data internally.

    This can correspond to a lem, rdg, or witDetail element in the collation.

    Attributes:
        id: The ID string of this reading, which should be unique within its parent app element.
        type: A string representing the type of reading. Examples include "reconstructed", "defective", "orthographic", "subreading", "ambiguous", "overlap", and "lac".
        text: Serialization of the contents of this element.
        wits: A list of sigla referring to witnesses that support this reading.
        targets: A list of other reading ID strings to which this reading corresponds. 
        For substantive readings, this should be empty. For ambiguous readings, it should contain references to the readings that might correspond to this one.
    """

    def __init__(self, _id: str, _type: str, _text: str, _wits: List[str], _targets: List[str], verbose: bool = False):
        """Constructs a new Reading instance with the specified fields."""
        self.id = _id
        self.type = _type
        self.text = _text
        self.wits = list(_wits)
        self.targets = list(_targets)
        if verbose:
            print(f"New Reading (id: {self.id}, type: {self.type}, wits: {str(self.wits)}, targets: {str(self.targets)}, text: {self.text if self.text is not None else ''})")

    @classmethod
    def from_xml(cls, xml: et.Element, verbose: bool = False):
        """Constructs a new Reading instance from a VMR XML segmentReading element.
        Optionally, the reading's type can be set to "subreading" if the reading has support from at most one witness.

        Args:
            xml: A VMR XML segmentReading element.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        # Set the ID of this Reading based on the segmentReading's label:
        _id = xml.get("label").strip("♦").strip()
        # Retrieve the type of this Reading from its label:
        _type = None
        if defective_reading_label_pattern.match(_id):
            _type = "defective"
        elif orthographic_reading_label_pattern.match(_id):
            _type = "orthographic"
        elif _id == overlap_label:
            _type = "overlap"
        elif _id == unclear_label:
            _type = "unclear"
        elif _id == ambiguous_label:
            _type = "ambiguous"
        elif _id == lac_label:
            _type = "lac"
        # If this reading is ambiguous, then the reading attribute contains its target readings; 
        # remove any "_f" suffixes from this string and split the remaining text on the "/" token:
        _targets = []
        if _type == "ambiguous":
            _targets = xml.get("reading").replace("_f", "").split("/")
        # Get the witness list for this reading:
        _wits = xml.get("witnesses").split()
        # Finally, get the text.
        # If the reading type is not "ambiguous", then the reading attribute will contain a proper reading, a string indicating an omission, or nothing (in the case of overlaps, unclear retroversions, and lacunae)
        _text = None
        if _type not in ["ambiguous", "unclear", "overlap", "lac"]:
            if xml.get("reading") is not None and xml.get("reading") != omission_string:
                _text = xml.get("reading")
        return cls(_id, _type, _text, _wits, _targets, verbose)

    def to_xml(self):
        """Returns a rdg or witDetail TEI XML element constructed from this Reading.

        Returns:
            An XML element with attributes matching those of this Reading.
        """
        tag = "{%s}rdg" % tei_ns if len(self.targets) == 0 and self.type not in ["ambiguous", "unclear", "overlap", "lac"] else "{%s}witDetail" % tei_ns
        xml = et.Element(tag, nsmap = {None: tei_ns})
        if self.id is not None:
            xml.set("n", self.id)
        if self.type is not None:
            xml.set("type", self.type)
        xml.set("wit", " ".join(self.wits))
        if len(self.targets) > 0:
            xml.set("target", " ".join(self.targets))
        # Set the xml:lang attribute of this reading based on its text, and add its text:
        if self.text is not None:
            if greek_rdg_pattern.match(self.text):
                pass # Greek is the language of the whole collation and does not need to be specified here
            elif latin_rdg_pattern.match(self.text):
                xml.set('{%s}lang' % xml_ns, "lat")
            elif syriac_rdg_pattern.match(self.text):
                xml.set('{%s}lang' % xml_ns, "syr")
            elif coptic_rdg_pattern.match(self.text):
                xml.set('{%s}lang' % xml_ns, "cop")
            xml.text = self.text
        return xml