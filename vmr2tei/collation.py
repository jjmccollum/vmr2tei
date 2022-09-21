#!/usr/bin/env python3

import time # to time calculations for users
import re # for parsing augmented witness sigla
from lxml import etree as et # for reading VMR XML inputs and writing TEI XML output

from .common import * # import variables from the common support 
from .witness import Witness
from .variation_unit import VariationUnit

class Collation():
    """Base class for storing VMR XML collation data internally.

    Attributes:
        book: A string representing the book for which this Collation contains data. 
        It is used to select the appropriate data sets (such as the witnesses represented by the "Byz" siglum in a given book) for cleaning up the collation data.
        witnesses: A list of Witnesses contained in this Collation.
        witness_inds_by_id: A dictionary mapping base witness sigla to their indices in the witnesses list.
        variation_units: A list of VariationUnits contained in this Collation.
        singular_to_subreading: An optional flag indicating whether or not to set a reading's type to "subreading" if the reading does not already have a type and has support from at most one witness.
        verbose: An optional flag indicating whether or not to print status updates.
    """

    def __init__(self, book, singular_to_subreading: bool = False, verbose: bool = False):
        """Initializes a new Collation instance with the given parameters.

        Args:
            xml: A VMR XML segment element whose segmentReading children all have normalized witness lists.
            book: A string representing the book for which this Collation contains data.
            singular_to_subreading: An optional flag indicating whether or not to set each segmentReading child's type to "subreading" 
            if the reading does not already have a type and has support from at most one witness.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        self.book = book # name of the NT book to which the collation belongs
        self.witnesses = [] # internal list of Witness instances
        self.witness_inds_by_id = {} # internal dictionary mapping witness IDs to their indices in the list
        self.variation_units = [] # internal list of VariationUnit instances
        self.singular_to_subreading = singular_to_subreading # flag indicating whether or not to use type="subreading" for readings with singular support
        self.verbose = verbose # flag indicating whether or not to print timing and debugging details for the user

    def cleanup_witness_lists(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation, normalizes the witness lists of all of its segmentReading elements in-place.

        Args:
            xml: A VMR XML tree for a collation.
        """
        # Proceed for each segment:
        for segment in xml.xpath("//segment"):
            # Maintain a set of manuscript witnesses that are covered by all readings in this segment:
            covered_manuscripts_set = set()
            # In a first pass, normalize the witness lists for all readings in this segment:
            for segment_reading in segment.xpath(".//segmentReading"):
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
                witnesses_string = expand_parenthetical_suffixes(witnesses_string)
                # Normalize all the versional witness sigla for easier parsing:
                witnesses_string = normalize_versional_sigla(witnesses_string)
                # Now update the segmentReading's wit attribute in-place:
                segment_reading.set("witnesses", witnesses_string)
                # Then add the manuscripts in this updated witness list to the set of covered manuscripts:
                wits = witnesses_string.split()
                for wit in wits:
                    # If this siglum does not look like a manuscript or looks like a corrector, then skip it:
                    if not manuscript_witness_pattern.match(wit) or corrector_pattern.search(wit):
                        continue
                    # Otherwise, get its base siglum and add that to the set of covered manuscripts:
                    wit_id = get_base_siglum(wit, ignored_manuscript_suffix_pattern)
                    covered_manuscripts_set.add(wit_id)
            # In a second pass, replace the "Byz" siglum with a string of appropriate witnesses:
            remaining_byz_witnesses = [wit for wit in byz_witnesses_by_book[self.book] if wit not in covered_manuscripts_set]
            for segment_reading in segment.xpath(".//segmentReading"):
                witnesses_string = segment_reading.get("witnesses")
                if "Byz" in witnesses_string:
                    witnesses_string = witnesses_string.replace("Byz", " ".join(remaining_byz_witnesses))
                    segment_reading.set("witnesses", witnesses_string)
    
    def parse_witnesses(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation (that is assumed to have been modified by the cleanup_witness_lists method),
        populates this Collation's witnesses list using the witnesses cited in XML's variant reading elements.

        Args:
            xml: A VMR XML tree for a collation with normalized witness lists.
        """
        if self.verbose:
            print("Parsing witnesses from VMR XML...")
        t0 = time.time()
        # Then proceed for each reading element:
        for segment_reading in xml.xpath("//segmentReading"):
            # Split its witness sigla over spaces and proceed for each siglum:
            wits = segment_reading.get("witnesses").split()
            for wit in wits:
                wit_id = wit
                wit_type = None
                # If this witness siglum already corresponds to an existing witness, then skip it:
                if wit_id in self.witness_inds_by_id:
                    continue
                # Otherwise, check if this siglum is for a manuscript:
                if papyrus_pattern.match(wit_id):
                    wit_type = "papyrus"
                    wit_id = get_base_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif majuscule_pattern.match(wit_id):
                    wit_type = "majuscule"
                    wit_id = get_base_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif minuscule_pattern.match(wit_id):
                    wit_type = "minuscule"
                    wit_id = get_base_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif lectionary_pattern.match(wit_id):
                    wit_type = "lectionary"
                    wit_id = get_base_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                # If not, check if it is a versional witness (all of them should now be normalized to have the versional prefix pattern):
                elif version_start_pattern.match(wit_id):
                    wit_type = "version"
                    # If this witness looks like a manuscript (e.g., if it is an Old Latin manuscript), then strip any ignored manuscript suffixes from it:
                    if manuscript_witness_pattern.match(wit_id):
                        wit_id = get_base_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    # NOTE: Ideally, the situation below should result in all copies of the version's sigla in this unit being moved to an ambiguous reading,
                    # but this is better handled in the preparation of the data than in the parsing.
                    # If this witness ends with "ms" or "mss", then its testimony is divided here; treat it as lacunose:
                    if ignored_version_suffix_pattern.search(wit):
                        continue
                # If none of these patterns matches, then assume the witness siglum is for a father and use it as-is:
                else:
                    wit_type = "father"
                    # NOTE: Ideally, situations involving divided manuscript attestation should result in all copies of the father's sigla in this unit being moved to an ambiguous reading,
                    # but this is better handled in the preparation of the data than in the parsing.
                    if ignored_patristic_suffix_pattern.search(wit):
                        continue
                # If this witness looks like a manuscript and has a corrector suffix, then use the "corrector" type instead:
                if manuscript_witness_pattern.match(wit_id) and corrector_pattern.search(wit_id):
                    if wit_id not in self.witness_inds_by_id:
                        # If this corrector is a first-hand corrector, then change "*VC" to "*C":
                        if wit_id.endswith("*VC"):
                            wit_id = wit_id.replace("*VC", "*C")
                        witness = Witness(wit_id, "corrector", self.verbose)
                        self.witnesses.append(witness)
                        self.witness_inds_by_id[wit_id] = len(self.witnesses) - 1
                # Otherwise, check if a Witness with this siglum has already been added, and add a new Witness if not:
                else:
                    if wit_id not in self.witness_inds_by_id:
                        witness = Witness(wit_id, wit_type, self.verbose)
                        self.witnesses.append(witness)
                        self.witness_inds_by_id[wit_id] = len(self.witnesses) - 1
        # Finally, sort the witnesses list and update the dictionary mapping their IDs to their indices:
        self.witnesses.sort()
        for i, wit in enumerate(self.witnesses):
            wit_id = wit.id
            self.witness_inds_by_id[wit_id] = i
        t1 = time.time()
        if self.verbose:
            print(f"Done parsing {len(self.witnesses)} witnesses in {(t1 - t0):0.4f}s.")

    def postprocess_witness_lists(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation (that is assumed to have been modified by the cleanup_witness_lists method),
        modifies the XML tree in-place by removing witness sigla whose base forms are not in this Collation's witnesses list, normalizing first-hand corrector sigla,
        and sorting the witness lists for all readings.

        Args:
            xml: A VMR XML tree for a collation with normalized witness lists.
        """
        # Proceed for each segment:
        for segment in xml.xpath("//segment"):
            # In a first pass, normalize the witness lists for all readings in this segment:
            for segment_reading in segment.xpath(".//segmentReading"):
                new_wits = []
                # Get its witness string:
                witnesses_string = segment_reading.get("witnesses")
                # Then process the manuscripts in this updated witness:
                wits = witnesses_string.split()
                for wit in wits:
                    # If this siglum looks like a manuscript, then check if its siglum stripped of ignored manuscript suffixes corresponds to a known witness:
                    if manuscript_witness_pattern.match(wit):
                        base_siglum = get_base_siglum(wit, ignored_manuscript_suffix_pattern)
                        # If this is a first-hand corrector, then change "*VC" to "*C" (because the V doesn't get removed in the get_base_siglum call):
                        if base_siglum.endswith("*VC"):
                            base_siglum = base_siglum.replace("*VC", "*C")
                        if base_siglum in self.witness_inds_by_id:
                            if base_siglum.endswith("*C"):
                                new_wits.append(wit.replace("*VC", "*C"))
                            else:
                                new_wits.append(wit)
                    # Otherwise, if this siglum looks like a versional witness, then skip it if it has any of the ignored versional suffixes.
                    # NOTE: Ideally, the situation below should result in all copies of the version's sigla in this unit being moved to an ambiguous reading,
                    # but this is better handled in the preparation of the data than in the parsing.
                    elif version_start_pattern.match(wit):
                        if not ignored_version_suffix_pattern.search(wit):
                            new_wits.append(wit)
                    # Otherwise, if this siglum looks like a patristic witness, then skip it if it has any of the ignored patristic suffixes.
                    # NOTE: Ideally, either of the situations below should result in all copies of the father's sigla in this unit being moved to an ambiguous reading,
                    # but this is better handled in the preparation of the data than in the parsing.
                    else:
                        if not ignored_father_suffix_pattern.search(wit):
                            new_wits.append(wit)
                # Then replace the original witness string with a witness string consisting of the retained witnesses:
                segment_reading.set("witnesses", " ".join(new_wits))

    def parse_segments(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation (that is assumed to have been modified by the cleanup_witness_lists method),
        parse its segments internally in this Collation.

        Args:
            xml: A VMR XML tree for a collation with normalized witness lists.
        """
        if self.verbose:
            print("Parsing variation units from VMR XML...")
        t0 = time.time()
        # Process each variation unit one at a time:
        for segment in xml.xpath("//segment"):
            vu = VariationUnit(segment, self.singular_to_subreading, self.verbose)
            self.variation_units.append(vu)
        t1 = time.time()
        if self.verbose:
            print(f"Done parsing {len(self.variation_units)} variation units in {(t1 - t0):0.4f}s.")

    def parse_xml(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation, clean up its witness lists and then parse its witnesses and segments internally in this Collation.

        Args:
            xml: A VMR XML tree for a collation.
        """
        self.cleanup_witness_lists(xml)
        self.parse_witnesses(xml)
        self.remove_unknown_witnesses(xml)
        self.parse_segments(xml)

    def to_xml(self):
        """Returns an app TEI XML element constructed from this Collation.

        Returns:
            A TEI XML ElementTree containing the data from this Collation.
        """
        # Initialize a namespace map to be used throughout the output XML tree:
        nsmap = {None: tei_ns, "xml": xml_ns}
        # Under this, add a TEI element to be populated later:
        tei = et.Element("TEI", nsmap=nsmap)
        # First, add a teiHeader element under the TEI element:
        teiHeader = et.Element("teiHeader")
        tei.append(teiHeader)
        # Under this, add a fileDesc element:
        fileDesc = et.Element("fileDesc")
        teiHeader.append(fileDesc)
        # Under this, add a titleStmt element under the fileDesc:
        titleStmt = et.Element("titleStmt")
        fileDesc.append(titleStmt)
        # Under this, add a title element:
        title = et.Element("title")
        title.text = "A collation of %s" % (self.book)
        titleStmt.append(title)
        # Next, add a publicationStmt element under the fileDesc:
        publicationStmt = et.Element("publicationStmt")
        p = et.Element("p")
        p.text = "Temporary publicationStmt for validation"
        publicationStmt.append(p)
        fileDesc.append(publicationStmt)
        # Next, add a sourceDesc element under the fileDesc:
        sourceDesc = et.Element("sourceDesc")
        fileDesc.append(sourceDesc)
        # Then add a listWit element under the sourceDesc:
        list_wit = et.Element("listWit")
        sourceDesc.append(list_wit)
        # Then add a witness element for each witness in this collation:
        for wit in self.witnesses:
            list_wit.append(wit.to_xml())
        # Then, add a text element with the appropriate main language under the TEI element:
        text = et.Element("text")
        text.set("{%s}lang" % xml_ns, "grc")
        tei.append(text)
        # Under this, add a body element:
        body = et.Element("body")
        text.append(body)
        # Add a div element for the book under the body element:
        book = et.Element("div")
        book.set("type", "book")
        book.set("n", self.book)
        body.append(book)
        # Then add the variation units under this div:
        for vu in self.variation_units:
            book.append(vu.to_xml())
        # Then clean up the namespaces for the XML:
        et.cleanup_namespaces(tei)
        # Then return the ElementTree rooted at the TEI element:
        return et.ElementTree(tei)