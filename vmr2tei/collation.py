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
                    wit_id = get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif majuscule_pattern.match(wit_id):
                    wit_type = "majuscule"
                    wit_id = get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif minuscule_pattern.match(wit_id):
                    wit_type = "minuscule"
                    wit_id = get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif lectionary_pattern.match(wit_id):
                    wit_type = "lectionary"
                    wit_id = get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                # If not, check if it is a versional witness (all of them should now be normalized to have the versional prefix pattern):
                elif version_start_pattern.match(wit_id):
                    wit_type = "version"
                    # If this witness looks like a manuscript, then strip any ignored manuscript suffixes from it:
                    if manuscript_witness_pattern.match(wit_id):
                        wit_id = get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    # TODO: Ideally, the situation below should result in all copies of the version's sigla in this unit being moved to an ambiguous reading,
                    # but this is better handled in the preparation of the data than in the parsing.
                    # If this witness ends with "ms" or "mss", then its testimony is divided here; treat it as lacunose:
                    if wit_id.endswith("ms") or wit_id.endswith("mss"):
                        continue
                # If none of these patterns matches, then assume the witness siglum is for a father and use it as-is:
                else:
                    wit_type = "father"
                    # TODO: Ideally, either of the situations below should result in all copies of the father's sigla in this unit being moved to an ambiguous reading,
                    # but this is better handled in the preparation of the data than in the parsing.
                    # If this witness has a "T" suffix, then it refers to the lemma of the father's commentary in disagreement with the commentary proper (which is indicated by the unsuffixed patristic siglum);
                    # we will ignore it to avoid confusing it with the commentary:
                    if wit_id.endswith("T"):
                        continue
                    # If this witness ends with "ms" or "mss", then its testimony is divided here; treat it as lacunose:
                    if wit_id.endswith("ms") or wit_id.endswith("mss"):
                        continue
                # If this witness looks like a manuscript and has a corrector suffix, then use the "corrector" type instead:
                if manuscript_witness_pattern.match(wit_id) and corrector_pattern.search(wit_id):
                    if wit_id not in self.witness_inds_by_id:
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
        cleanup_witness_lists(xml)
        self.parse_witnesses(xml)
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