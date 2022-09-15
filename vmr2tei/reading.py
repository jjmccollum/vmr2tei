#!/usr/bin/env python3

from typing import List
from lxml import etree as et

from .common import *


class Reading:
    """Base class for storing TEI XML reading data internally.

    This can correspond to a lem, rdg, or witDetail element in the collation.

    Attributes:
        id: The ID string of this reading, which should be unique within its parent app element.
        type: A string representing the type of reading. Examples include "reconstructed", "defective", "orthographic", "subreading", "ambiguous", "overlap", and "lac".
        text: Serialization of the contents of this element.
        wits: A list of sigla referring to witnesses that support this reading.
        targets: A list of other reading ID strings to which this reading corresponds. For substantive readings, this should be empty. For ambiguous readings, it should contain references to the readings that might correspond to this one. For overlap readings, it should contain a reference to the reading from the overlapping variation unit responsible for the overlap.
        certainties: A dictionary mapping target reading IDs to floating-point certainty values.
    """

    def __init__(self, id: str = None, rdg_type: str = None, wits: List[str] = [], targets: List[str] = [], text: str = None, verbose: bool = False):
        """Constructs a new Reading instance from the TEI XML input.

        Args:
            id: A string representing the ID of this Reading. It will be written to the rdg element's n attribute in case it is not unique.
            rdg_type: A string representing the type of this Reading.
            wits: A list of sigla for the witnesses supporting this Reading.
            targets: A list of reading numbers targeted by this Reading (in case it is an ambiguous reading).
            text: A string containing the text of this Reading.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        self.id = id
        self.type = rdg_type
        self.wits = wits
        self.targets = targets
        self.text = text
        if verbose:
            print("New Reading (id: %s, type: %s, wits: %s, targets: %s, text: %s)" % (self.id, self.type, str(self.wits), str(self.targets), self.text))

    def parse_xml(self, xml: et.Element, singular_to_subreading: bool = False):
        """Given a VMR XML segmentReading element, populate the fields of this Reading with the appropriate attributes.
        Optionally, the reading's type can be set to "subreading" if the reading has support from at most one witness.

        Args:
            xml: A VMR XML segmentReading element.
            singular_to_subreading: An optional flag indicating whether or not to set the reading's type to "subreading" if the reading does not already have a type and has support from at most one witness.
        """
        # Set this Reading's fields based on the input segmentReading:
        self.id = xml.get("label").replace("♦", "").strip() # remove diamonds and surrounding whitespace
        # Retrieve the type of this reading from its label:
        self.type = None
        if defective_reading_label_pattern.match(label):
            self.type = "defective"
        elif orthographic_reading_label_pattern.match(label):
            self.type = "orthographic"
        elif label == overlap_label:
            self.type = "overlap"
        elif label == ambiguous_label:
            self.type = "ambiguous"
        elif label == lac_label:
            self.type = "lac"
        # If this reading is ambiguous, then the reading attribute contains its target readings; 
        # remove any "_f" suffixes from this string and split the remaining text on the "/" token:
        self.targets = []
        if self.type == "ambiguous":
            self.targets = xml.get("reading").replace("_f", "").split("/")
        # Get the witness list for this reading:
        self.wits = xml.get("witnesses").split()
        # If the singular_to_subreading flag is set, then set the reading type to "subreading" if it is not already set and the witness list contains at most one entry:
        if singular_to_subreading and self.type is None and len(self.wits) <= 1:
            self.type = "subreading"
        # Finally, get the text.
        # If the reading type is not "ambiguous", then the reading attribute will contain a proper reading, a string indicating an omission, or nothing (in the case of overlaps and lacunae)
        self.text = None
        if self.type not in ["ambiguous", "overlap", "lac"]:
            if xml.text is not None and xml.text != omission_string:
                self.text = xml.text

    def to_xml(self):
        """Returns a rdg or witDetail TEI XML element constructed from this Reading.

        Returns:
            An XML element with attributes matching those of this Reading.
        """
        tag = "rdg" if len(self.targets) == 0 and self.type not in ["ambiguous", "overlap", "lac"] else "witDetail"
        xml = et.Element(tag, nsmap={None: tei_ns})
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