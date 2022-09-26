#!/usr/bin/env python3

import time # to time calculations for users
from typing import List
from lxml import etree as et # for reading TEI XML inputs

from .common import *
from .reading import Reading

class VariationUnit:
    """Base class for storing TEI XML variation unit data internally.

    This corresponds to an app element in the collation.

    Attributes:
        id: The ID string of this variation unit, which should be unique.
        readings: A list of Readings contained in this VariationUnit.
    """

    def __init__(self, xml: et.Element, singular_to_subreading: bool = False, verbose: bool = False):
        """Constructs a new VariationUnit instance from a VMR XML segment element.

        Args:
            xml: A VMR XML segment element whose segmentReading children all have normalized witness lists.
            singular_to_subreading: An optional flag indicating whether or not to set each segmentReading child's type to "subreading" 
            if the reading does not already have a type and has support from at most one witness.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        t0 = time.time()
        # Combine the segment's verse and wordsegs attributes into a single ID:
        self.id = ""
        if xml.get("verse") is not None:
            self.id += xml.get("verse")
            if xml.get("wordsegs") is not None:
                self.id += "/" + xml.get("wordsegs")
        # Initialize its list of readings:
        self.readings = []
        for segment_reading in xml.xpath(".//segmentReading"):
            rdg = Reading(segment_reading, singular_to_subreading, verbose)
            self.readings.append(rdg)
        t1 = time.time()
        if verbose:
            print(f"New VariationUnit (id: {self.id}, {len(self.readings)} readings) constructed in {(t1-t0):0.4f}s.")

    def to_xml(self):
        """Returns an app TEI XML element constructed from this VariationUnit.

        Returns:
            An XML Element with attributes matching those of this VariationUnit and child elements corresponding to its Readings.
        """
        xml = et.Element("{%s}app" % tei_ns)
        if self.id is not None:
            xml.set("n", self.id)
        for rdg in self.readings:
            xml.append(rdg.to_xml())
        return xml