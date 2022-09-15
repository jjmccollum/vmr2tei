#!/usr/bin/env python3

from typing import List
from lxml import etree as et  # for reading TEI XML inputs

from common import *
from reading import Reading

class VariationUnit:
    """Base class for storing TEI XML variation unit data internally.

    This corresponds to an app element in the collation.

    Attributes:
        id: The ID string of this variation unit, which should be unique.
        readings: A list of Readings contained in this VariationUnit.
    """

    def __init__(self, loc: str = None, sequence: str = None, readings: List[Reading] = [], verbose: bool = False):
        """Constructs a new VariationUnit instance from the TEI XML input.

        Args:
            loc: A string representing the location of this VariationUnit (as a verse reference).
            sequence: A string representing the starting and ending indices of this VariationUnit in the lemma for the verse.
            readings: A List of Readings contained in this VariationUnit.
            verbose: An optional boolean flag indicating whether or not to print status updates.
        """
        # Combine the loc, from, and to attributes into a single ID:
        self.id = loc + "/" + app_from
        if app_to != app_from:
            self.id += "-" + app_to
        # Initialize its list of readings:
        self.readings = []
        # Now parse the app element to populate these data structures:
        self.parse(xml, verbose)
        if verbose:
            print("New VariationUnit (id: %s, %d readings)" % (self.id, len(self.readings)))

    def to_xml(self):
        """Returns an app TEI XML element constructed from this VariationUnit.

        Returns:
            An XML Element with attributes matching those of this VariationUnit and child elements corresponding to its Readings.
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