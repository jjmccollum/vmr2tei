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

    def __init__(self, loc: str = None, app_from: str = None, app_to: str = None, readings: List[Reading] = [], verbose: bool = False):
        """Constructs a new VariationUnit instance from the TEI XML input.

        Args:
            loc: A string representing the location of this VariationUnit.
            app_from: A string representing the starting index of this VariationUnit in the lemma.
            app_to: A string representing the ending index of this VariationUnit in the lemma.
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

    def get_byz_witnesses(self, xml: et.Element):
        """Given an XML Element representing a segment element, return a list of Byzantine witness sigla that do not appear in any reading.
        The output list can be used as a replacement pattern for the "Byz" siglum in a variation unit.

        Args:
            xml: A VMR XML segment element.

        Returns:
            A list of witnesses included under the "Byz" siglum that are not included in any segmentReading in the input segment element.
        """
        covered_witnesses = set()
        # Add the remaining witnesses listed for all readings to the internal witness list:
        for segment_reading in xml.xpath(".//segmentReading"):
            # Get its witness string:
            witnesses_string = segment_reading.get("witnesses")
            # The VMR collations sometimes erroneously leave in periods for spaces; replace them accordingly:
            witnesses_string = witnesses_string.replace(".", " ")
            # Remove any square brackets around witnesses:
            witnesses_string = witnesses_string.replace("[", "").replace("]", "")
            # Remove any right angle brackets after versional witnesses:
            witnesses_string = witnesses_string.replace(">", "")
            # Remove any erroneous spaces after colons:
            witnesses_string = witnesses_string.replace(": ", ":")
            # Remove any erroneous double spaces:
            witnesses_string = witnesses_string.replace("  ", " ")
            # Remove any escaped spaces at the end of the witnesses list:
            witnesses_string = witnesses_string.replace(" &nbsp;", "")
            # Expand out any parenthetical suffixes in the witness string:
            witnesses_string = self.expand_parenthetical_suffixes(witnesses_string)
            # Normalize all the versional witness sigla for easier parsing:
            witnesses_string = self.normalize_versional_sigla(witnesses_string)
            # Remove the "Byz" siglum (it can be ignored for now):
            witnesses_string = witnesses_string.replace("Byz", "")
            # Now split the witness sigla over spaces and proceed for each siglum:
            wits = witnesses_string.split()
            for wit in wits:
                # First, check if this siglum is for a manuscript:
                if papyrus_pattern.match(wit):
                    wit_type = "papyrus"
                    wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    covered_witnesses.add(wit_id)
                elif majuscule_pattern.match(wit):
                    wit_type = "majuscule"
                    wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    covered_witnesses.add(wit_id)
                elif minuscule_pattern.match(wit):
                    wit_type = "minuscule"
                    wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    covered_witnesses.add(wit_id)
                elif lectionary_pattern.match(wit):
                    wit_type = "lectionary"
                    wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    covered_witnesses.add(wit_id)
                else:
                    # All witnesses in the Byzantine set are manuscripts, so we can ignore all other witnesses
                    continue
        return [wit for wit in byz_witnesses if wit not in covered_witnesses]

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