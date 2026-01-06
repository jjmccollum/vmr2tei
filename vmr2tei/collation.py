#!/usr/bin/env python3

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
        include_a: An optional flag indicating whether or not to include the Ausgangstext (A) as an additional witness in the collation. Split-line readings will be treated as ambiguous readings for this witness.
        verbose: An optional flag indicating whether or not to print status updates.
    """

    def __init__(self, book, include_a: bool = False, verbose: bool = False):
        """Initializes a new Collation instance with the given parameters.

        Args:
            xml: A VMR XML segment element whose segmentReading children all have normalized witness lists.
            book: A string representing the book for which this Collation contains data.
            include_a: An optional flag indicating whether or not to include the Ausgangstext (A) as an additional witness in the collation. Split-line readings will be treated as ambiguous readings for this witness.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        self.book = book # name of the NT book to which the collation belongs
        self.witnesses = [] # internal list of Witness instances
        self.witness_inds_by_id = {} # internal dictionary mapping witness IDs to their indices in the list
        self.variation_units = [] # internal list of VariationUnit instances
        self.include_a = include_a # flag indicating whether or not to include the Ausgangstext (A) as a distinct witness
        self.verbose = verbose # flag indicating whether or not to print timing and debugging details for the user
        # If we are to include the Ausgangstext as a witness, then add it to the witness list now:
        if self.include_a:
            a_witness = Witness("A", "initial", None, None, self.verbose)
            self.witnesses.append(a_witness)
            self.witness_inds_by_id["A"] = 0

    def add_witnesses(self, xml: et.Element):
        """Given a VMR XML element representing a list of witnesses, populates this Collation's internal list of Witnesses.
        Witnesses without GA numbers or with spaces in their GA numbers are not added, as they would not occur in any variation unit's witness list.
        TODO: The Liste API seemingly does not have the data for versions and fathers nicely organized and dated yet, 
        so for now, this method assumes that the VMR XML element contains only manuscript entries.

        Args:
            xml: A VMR XML element for a witness list.
        """
        for manuscript in xml.xpath(".//manuscript"):
            ga_num = manuscript.get("gaNum")
            if ga_num is None or ga_num == "" or " " in ga_num:
                continue
            witness = Witness.from_xml(manuscript, self.verbose)
            self.witness_inds_by_id[ga_num] = len(self.witnesses)
            self.witnesses.append(witness)

    def cleanup_witness_lists(self, xml: et.Element):
        """Given a VMR XML element representing a segment, normalizes the witness lists of all of its segmentReading elements in-place.

        Args:
            xml: A VMR XML element for a segment.
        """
        # Maintain a set of manuscript witnesses that are covered by all readings in this segment:
        covered_manuscripts_set = set()
        # In a first pass, normalize the witness lists for all readings in this segment:
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
            # Replace superscript "ms" and "mss" suffixes with standard lowercase equivalents:
            witnesses_string = witnesses_string.replace("ᵐˢˢ", "mss").replace("ᵐˢ", "ms")
            # Replace superscript suffixes for the Harklean Syriac version with their standard uppercase equivalents:
            witnesses_string = witnesses_string.replace("ᵀ", "T").replace("ᴬ", "A").replace("ᴹ", "M")
            # Replace the superscript suffix for one Arabic version's margin with its standard lowercase equivalent:
            witnesses_string = witnesses_string.replace("ᵐᶢ", "mg")
            # Remove any escaped characters in the witnesses list:
            witnesses_string = witnesses_string.replace(" &nbsp;", "").replace("&gt;", "").replace("&lt;", "")
            # Replace the ECM notation for first-hand corrections and apparent first-hand corrections with simpler notation 
            # that looks like other corrector notation:
            witnesses_string = witnesses_string.replace("*C", "C0")
            witnesses_string = witnesses_string.replace("*VC", "C0V")
            # Expand out any parenthetical suffixes in the witness string:
            witnesses_string = expand_parenthetical_suffixes(witnesses_string)
            # Normalize all the versional witness sigla for easier parsing:
            witnesses_string = normalize_versional_sigla(witnesses_string)
            # Now update the segmentReading's wit attribute in-place:
            segment_reading.set("witnesses", witnesses_string)
            # Then add the manuscripts in this updated witness list to the set of covered manuscripts:
            wits = witnesses_string.split()
            for wit in wits:
                # If this siglum does not look like a manuscript, or if it looks like a corrector, then skip it:
                if not manuscript_witness_pattern.match(wit) or corrector_suffix_pattern.search(wit):
                    continue
                # Otherwise, get its base siglum and add that to the set of covered manuscripts:
                wit_id = get_base_siglum(wit, [ignored_manuscript_suffix_pattern, lection_suffix_pattern], [])
                covered_manuscripts_set.add(wit_id)
        # In a second pass, replace the "Byz" siglum with a string of appropriate witnesses:
        remaining_byz_witnesses = [wit for wit in byz_witnesses_by_book[self.book] if wit not in covered_manuscripts_set]
        for segment_reading in xml.xpath(".//segmentReading"):
            witnesses_string = segment_reading.get("witnesses")
            if "Byz" in witnesses_string:
                witnesses_string = witnesses_string.replace("Byz", " ".join(remaining_byz_witnesses))
                segment_reading.set("witnesses", witnesses_string)
        
    def add_segment(self, xml: et.Element):
        """Given a VMR XML element representing a segment (that is assumed to have been modified by the cleanup_witness_lists method),
        preprocess the XML element in place, parse it as a VariationUnit instance, and add it to the internal storage of this Collation.

        Args:
            xml: A VMR XML element for a segment with normalized witness lists.
        """
        if self.verbose:
            print("Parsing variation unit from VMR XML...")
        self.cleanup_witness_lists(xml)
        vu = VariationUnit.from_xml(xml, self.include_a, self.verbose)
        self.variation_units.append(vu)

    def postprocess_witness_lists(self):
        """Post-process the witness list for this Collation and the witness lists for all of its Readings,
        Removing any witnesses whose base sigla are not in the Collation's witness list from the Readings,
        then removing any witnesses from the Collation's witness list that are not found in any Reading,
        then adding correctors and other derived witnesses from the Readings to the Collation's witness list,
        and then sorting the Collation's witness list accordingly.
        """
        # First, filter all of the reading witness lists, and populate a dictionary 
        # that maps witnesses whose base sigla are in the Collation's witness list to key tuples for sorting:
        sort_keys_by_id = {}
        for vu in self.variation_units:
            for rdg in vu.readings:
                new_wits = []
                for wit in rdg.wits:
                    # Determine which type of witness this is:
                    if manuscript_witness_pattern.match(wit):
                        # For manuscripts, get base sigla with and without corrector suffixes,
                        # as we want to add correctors as separate witnesses to this Collation's witness list:
                        first_hand_base_siglum = get_base_siglum(wit, [ignored_manuscript_suffix_pattern, corrector_suffix_pattern, lection_suffix_pattern], [])
                        corrector_base_siglum = get_base_siglum(wit, [ignored_manuscript_suffix_pattern, lection_suffix_pattern], [corrector_suffix_pattern])
                        # Is the first hand's base siglum in this Collation's witness list?
                        if first_hand_base_siglum in self.witness_inds_by_id:
                            # If the first hand's base siglum matches the corrector's siglum, then this witness is not a corrector;
                            # add it to the sort key dictionary, if it isn't already present:
                            if first_hand_base_siglum == corrector_base_siglum:
                                new_wits.append(wit)
                                if corrector_base_siglum not in sort_keys_by_id:
                                    # Use an expanded sort key tuple for correctors, so they will be sorted just after their corresponding first hands:
                                    sort_keys_by_id[corrector_base_siglum] = manuscript_siglum_key(corrector_base_siglum)
                            # Otherwise, this may be a corrector or something like a lection or duplicated reading;
                            # add it as a separate witness only if it is a corrector, commentary reading, or alternate reading, 
                            # and it is not a lection or repeated portion of text:
                            elif corrector_suffix_pattern.search(corrector_base_siglum) and not lection_suffix_pattern.search(corrector_base_siglum):
                                new_wits.append(wit)
                                if corrector_base_siglum not in sort_keys_by_id:
                                    # Use an expanded sort key tuple for correctors, so they will be sorted just after their corresponding first hands:
                                    sort_keys_by_id[corrector_base_siglum] = manuscript_siglum_key(corrector_base_siglum)
                            continue
                    if version_start_pattern.search(wit):
                        base_siglum = get_base_siglum(wit, [ignored_version_suffix_pattern], [])
                         # Is the base siglum is in this Collation's witness list?
                        if base_siglum in self.witness_inds_by_id:
                            # If so, then add the base siglum to the new witness list for this reading and the sort keys dictionary, stripped of its previous suffixes:
                            new_wits.append(base_siglum)
                            if base_siglum not in sort_keys_by_id:
                                sort_keys_by_id[base_siglum] = tuple([self.witness_inds_by_id[base_siglum]])
                        continue
                    # Otherwise, this must be a patristic witness:
                    base_siglum = get_base_siglum(wit, [ignored_father_suffix_pattern], [])
                    # Is the base siglum is in this Collation's witness list?
                    if base_siglum in self.witness_inds_by_id:
                        # If so, then add the base siglum to the new witness list for this reading and the sort keys dictionary, stripped of its previous suffixes:
                        new_wits.append(base_siglum)
                        if base_siglum not in sort_keys_by_id:
                            sort_keys_by_id[base_siglum] = tuple([self.witness_inds_by_id[base_siglum]])
                # Then set the reading's witness list to the new, filtered list, sorted by their sort keys:
                def wit_sort_key(wit):
                    if manuscript_witness_pattern.match(wit):
                        return sort_keys_by_id[get_base_siglum(wit, [ignored_manuscript_suffix_pattern, lection_suffix_pattern], [corrector_suffix_pattern])]
                    elif version_start_pattern.search(wit):
                        return sort_keys_by_id[get_base_siglum(wit, [ignored_version_suffix_pattern], [])]
                    return sort_keys_by_id[get_base_siglum(wit, [ignored_father_suffix_pattern], [])]
                rdg.wits = sorted(new_wits, key=lambda wit: wit_sort_key(wit))
        # Next, filter the Collation's witness list, excluding any witnesses not encountered in any reading:
        new_witnesses = []
        for witness in self.witnesses:
            if witness.id not in sort_keys_by_id:
                del self.witness_inds_by_id[witness.id]
                continue
            new_witnesses.append(witness)
        self.witnesses = new_witnesses
        # Then add new witness elements (without date ranges) to the Collation's witness list:
        for wit in sort_keys_by_id:
            if wit not in self.witness_inds_by_id:
                # Determine the type of this witness:
                wit_type = None
                if manuscript_witness_pattern.match(wit):
                    if corrector_suffix_pattern.search(wit):
                        wit_type = "corrector"
                    else:
                        wit_type = None
                elif version_start_pattern.match(wit):
                    wit_type = "version"
                else:
                    wit_type = "father"
                witness = Witness(wit, wit_type, None, None, self.verbose)
                self.witness_inds_by_id[witness.id] = -1 # this will be updated shortly
                self.witnesses.append(witness)
        # Then sort the witness list in-place and update the ID-to-index dictionary:
        self.witnesses.sort(key=lambda witness: sort_keys_by_id[witness.id])
        self.witness_inds_by_id = {}
        for i, witness in enumerate(self.witnesses):
            self.witness_inds_by_id[witness.id] = i

    def to_xml(self):
        """Returns an app TEI XML element constructed from this Collation.

        Returns:
            A TEI XML ElementTree containing the data from this Collation.
        """
        # Initialize a namespace map to be used throughout the output XML tree:
        nsmap = {None: tei_ns, "xml": xml_ns}
        # Under this, add a TEI element to be populated later:
        tei = et.Element("{%s}TEI" % tei_ns, nsmap=nsmap)
        # First, add a teiHeader element under the TEI element:
        teiHeader = et.Element("{%s}teiHeader" % tei_ns)
        tei.append(teiHeader)
        # Under this, add a fileDesc element:
        fileDesc = et.Element("{%s}fileDesc" % tei_ns)
        teiHeader.append(fileDesc)
        # Under this, add a titleStmt element under the fileDesc:
        titleStmt = et.Element("{%s}titleStmt" % tei_ns)
        fileDesc.append(titleStmt)
        # Under this, add a title element:
        title = et.Element("{%s}title" % tei_ns)
        title.text = "A collation of %s" % (self.book)
        titleStmt.append(title)
        # Next, add a publicationStmt element under the fileDesc:
        publicationStmt = et.Element("{%s}publicationStmt" % tei_ns)
        p = et.Element("p")
        p.text = "Temporary publicationStmt for validation"
        publicationStmt.append(p)
        fileDesc.append(publicationStmt)
        # Next, add a sourceDesc element under the fileDesc:
        sourceDesc = et.Element("{%s}sourceDesc" % tei_ns)
        fileDesc.append(sourceDesc)
        # Then add a listWit element under the sourceDesc:
        list_wit = et.Element("{%s}listWit" % tei_ns)
        sourceDesc.append(list_wit)
        # Then add a witness element for each witness in this collation:
        for wit in self.witnesses:
            list_wit.append(wit.to_xml())
        # Then, add a text element with the appropriate main language under the TEI element:
        text = et.Element("{%s}text" % tei_ns)
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