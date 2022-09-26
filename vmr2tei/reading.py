#!/usr/bin/env python3

import time # to time calculations for users
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

    def __init__(self, xml: et.Element, singular_to_subreading: bool = False, verbose: bool = False):
        """Constructs a new Reading instance from a VMR XML segmentReading element.
        Optionally, the reading's type can be set to "subreading" if the reading has support from at most one witness.

        Args:
            xml: A VMR XML segmentReading element.
            singular_to_subreading: An optional flag indicating whether or not to set the reading's type to "subreading" if the reading does not already have a type and has support from at most one witness.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        t0 = time.time()
        # Set the ID of this Reading based on the segmentReading's label:
        self.id = xml.get("label").replace("♦", "").strip() # remove diamonds and surrounding whitespace
        # Retrieve the type of this Reading from its label:
        self.type = None
        if defective_reading_label_pattern.match(self.id):
            self.type = "defective"
        elif orthographic_reading_label_pattern.match(self.id):
            self.type = "orthographic"
        elif self.id == overlap_label:
            self.type = "overlap"
        elif self.id == unclear_label:
            self.type = "unclear"
        elif self.id == ambiguous_label:
            self.type = "ambiguous"
        elif self.id == lac_label:
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
        # If the reading type is not "ambiguous", then the reading attribute will contain a proper reading, a string indicating an omission, or nothing (in the case of overlaps, unclear retroversions, and lacunae)
        self.text = None
        if self.type not in ["ambiguous", "unclear", "overlap", "lac"]:
            if xml.get("reading") is not None and xml.get("reading") != omission_string:
                self.text = xml.get("reading")
        t1 = time.time()
        if verbose:
            print(f"New Reading (id: {self.id}, type: {self.type}, wits: {str(self.wits)}, targets: {str(self.targets)}, text: {self.text if self.text is not None else ''}) constructed in {(t1 - t0):0.4f}s.")

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