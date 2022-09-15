#!/usr/bin/env python3

import time # to time calculations for users
import re # for parsing augmented witness sigla
from lxml import etree as et # for reading VMR XML inputs and writing TEI XML output
import urllib.request # for making HTTP requests to the VMR API
import numpy as np # matrix support

from common import * # import variables from the common support 
from witness import Witness
from variation_unit import VariationUnit

"""
Base class for reading and converting collation data.
"""
class Collation():
    """
	Constructs a new Collation with the given settings.
	"""
    def __init__(self, singular_to_subreading: bool = False, verbose: bool = False):
        self.book = "" # name of the NT book to which the collation belongs
        self.witnesses = [] # internal list of Witness instances
        self.witness_inds_by_id = {} # internal dictionary mapping witness IDs to their indices in the list
        self.variation_units = [] # internal list of VariationUnit instances
        self.singular_to_subreading = singular_to_subreading # flag indicating whether or not to use type="subreading" for readings with singular support
        self.verbose = verbose # flag indicating whether or not to print timing and debugging details for the user

    def get_base_manuscript_siglum(self, siglum: str, regex: re.Pattern = all_manuscript_suffix_pattern):
        """Given a manuscript witness siglum and a regex of suffixes to remove from it,
        strips all suffixes described by the regex from the siglum until the remaining siglum corresponds to a witness in the witnesses list
        or no further suffixes can be found.
        The resulting base siglum is returned.
        The suffix regex defaults to the common module's manuscript_suffix_pattern.

        Args:
            siglum: A witness siglum potentially consisting of multiple suffixes that can be stripped from the base witness (e.g., "01*f").
            regex: A regular expression pattern to identify unwanted suffixes from the siglum.

        Returns:
            A string representing the base siglum stripped of unwanted suffixes.
        """
        base_manuscript_siglum = siglum
        suffix_found = True
        while (suffix_found):
            suffix_found = False
            # If the current siglum corresponds to a witness, then we're done:
            if base_manuscript_siglum in self.witness_inds_by_id:
                return base_manuscript_siglum
            # Otherwise, check if it has a suffix to be removed, and remove the suffix if so:
            if regex.search(base_manuscript_siglum):
                suffix_found = True
                suffix = regex.search(base_manuscript_siglum).group()
                base_manuscript_siglum = base_manuscript_siglum[:-len(suffix)]
        # If we reach this point, then suffixes may have been removed, but the base siglum never matched a known witness;
        # return the siglum stripped of any suffixes we found on it:
        return base_manuscript_siglum

    def split_versional_witnesses(self, siglum: str, regex: re.Pattern):
        """Given a versional witness siglum and a regex of prefixes to remove from it,
        returns a list of all prefixes identified in it.

        Args:
            siglum: A witness siglum potentially consisting of multiple versional witness sigla (e.g., "SBM").
            regex: A regular expression pattern to extract witness sigla from the combined siglum.

        Returns:
            A list of extracted versional witness sigla.
        """
        old_string = siglum
        extracted_prefixes = []
        prefix_found = True
        while (prefix_found):
            prefix_found = False
            # If the current string contains a prefix to be extracted, then do so:
            if regex.match(old_string):
                prefix_found = True
                prefix = regex.match(old_string).group()
                old_string = old_string[len(prefix):]
                extracted_prefixes.append(prefix)
        return extracted_prefixes

    def expand_parenthetical_suffixes(self, wit_str: str):
        """Given a string of witness sigla, expands any base sigla followed by one or more suffixes in parentheses
        so that they all appear as full sigla with a common base.

        Args:
            wit_str: A string of witnesses for a reading.

        Returns:
            A copy of the original string with suffixes in parentheses
            expanded into full witness sigla sharing the base siglum of the witness preceding the parentheses. 
        """
        expanded_wit_str = wit_str
        matches = witness_with_parentheses_pattern.findall(wit_str)
        for match in matches:
            wit = match[0]
            suffixes = match[1].replace(" ", "").split(",")
            expanded_wits = []
            for suffix in suffixes:
                expanded_wit = wit + suffix
                expanded_wits.append(expanded_wit)
            expanded_wit_str = expanded_wit_str.replace(match[0] + "(" + match[1] + ")", " ".join(expanded_wits))
        return expanded_wit_str

    def normalize_versional_sigla(wit_str: str):
        """Given a string of witness sigla, normalizes all versional sigla in the string.
        The witness string with the normalized versional sigla is returned.

        Args:
            wit_str: A string of witnesses for a reading.
        
        Returns:
            A copy of the original string with versional sigla normalized 
            to begin with a prefix consisting of an abbreviation for the version language followed by a colon.
        """
        old_versional_sigla = []
        normalized_versional_sigla = []
        version_prefix = ""
        # First, split the string on whitespace:
        wits = wit_str.split()
        for wit in wits:
            # If we haven't entered the versional evidence block, then skip any entries that do not match the pattern of a versional evidence block:
            if version_prefix == "" and not version_start_pattern.search(wit):
                continue
            # Otherwise, if this is the start of a new versional evidence block, then update the current version prefix, and look up the siglum replacement for the appropriate version:
            if version_start_pattern.search(wit):
                # If this siglum contains a colon, the the part before the colon is the new version prefix and should be saved for later,
                # and the entire siglum is already correctly formatted:
                if ":" in wit:
                    version_prefix = wit.split(":")[0]
                    version_suffix = wit.split(":")[1]
                    # The suffix may contain multiple sigla concatenated together, so extract these sigla first and then construct a replacement string for all of them:
                    versional_witness_regex = None
                    if version_prefix == "L":
                        versional_witness_regex = latin_version_pattern
                    elif version_prefix == "S":
                        versional_witness_regex = syriac_version_pattern
                    elif version_prefix == "K":
                        versional_witness_regex = coptic_version_pattern
                    elif version_prefix == "Sl":
                        versional_witness_regex = slavonic_version_pattern
                    old_sigla = self.split_versional_witnesses(version_suffix, versional_witness_regex)
                    new_sigla = []
                    for old_siglum in old_sigla:
                        new_siglum = version_prefix + ":" + old_siglum
                        new_sigla.append(new_siglum)
                    normalized_siglum = " ".join(new_sigla)
                    old_versional_sigla.append(wit)
                    normalized_versional_sigla.append(normalized_siglum)
                # Otherwise, treat the siglum as a singleton versional siglum and add it to the list:
                else:
                    version_prefix = wit
                    normalized_siglum = version_prefix + ":" + wit
                    old_versional_sigla.append(wit)
                    normalized_versional_sigla.append(normalized_siglum)
            # Otherwise, assume we are still in the block of a previous version:
            else:
                normalized_siglum = version_prefix + ":" + wit
                old_versional_sigla.append(wit)
                normalized_versional_sigla.append(normalized_siglum)
        normalized_versional_sigla_str = wit_str.replace(" ".join(old_versional_sigla), " ".join(normalized_versional_sigla))
        return normalized_versional_sigla_str

    def cleanup_witness_lists(xml: et.ElementTree):
        """Given a VMR XML tree representing a collation, normalizes the witness lists of all of its segmentReading elements in-place.

        Args:
            xml: A VMR XML tree for a collation.
        """
        # Proceed for each segmentReading:
        for segment_reading in xml.xpath("//segmentReading"):
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
            # Now update the segmentReading's wit attribute in-place:
            segment_reading.set("wit", witnesses_string)
    
    def parse_witnesses(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation (that is assumed to have been modified by the cleanup_witness_lists method),
        populates this Collation's witnesses list using the witnesses cited in XML's variant reading elements.

        Args:
            xml: A VMR XML tree for a collation with normalized witness lists.
        """
        # Start by adding the Byzantine witnesses to the witness list:
        for wit in byz_witnesses:
            wit_type = ""
            wit_id = ""
            if papyrus_pattern.match(wit):
                wit_type = "papyrus"
                wit_id = wit
            elif majuscule_pattern.match(wit):
                wit_type = "majuscule"
                wit_id = wit
            elif minuscule_pattern.match(wit):
                wit_type = "minuscule"
                wit_id = wit
            elif lectionary_pattern.match(wit):
                wit_type = "lectionary"
                wit_id = wit
            witness = Witness(wit_id, wit_type, self.verbose)
            self.witnesses.append(witness)
            self.witness_inds_by_id[wit_id] = len(self.witnesses) - 1
        # Then proceed for each reading element:
        for segment in xml.xpath("//segmentReading"):
            # Split its witness sigla over spaces and proceed for each siglum:
            wits = witnesses_string.split()
            for wit in wits:
                wit_id = wit
                wit_type = None
                # If this witness siglum is the "Byz" siglum, then skip it (we have already added its constituent witnesses to the list):
                if wit_id == "Byz":
                    continue
                # If this witness siglum already corresponds to an existing witness, then skip it:
                if wit_id in self.witness_inds_by_id:
                    continue
                # Otherwise, check if this siglum is for a manuscript:
                if papyrus_pattern.match(wit_id):
                    wit_type = "papyrus"
                    wit_id = self.get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif majuscule_pattern.match(wit_id):
                    wit_type = "majuscule"
                    wit_id = self.get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif minuscule_pattern.match(wit_id):
                    wit_type = "minuscule"
                    wit_id = self.get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                elif lectionary_pattern.match(wit_id):
                    wit_type = "lectionary"
                    wit_id = self.get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                # If not, check if it is a versional witness (all of them should now be normalized to have the versional prefix pattern):
                elif version_start_pattern.match(wit_id):
                    wit_type = "version"
                    # If this witness looks like a manuscript, then strip any ignored manuscript suffixes from it:
                    if manuscript_witness_pattern.match(wit_id):
                        wit_id = self.get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
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
        self.witnesses.sort(key=lambda wit: wit_sort_key(wit))
        for i, wit in enumerate(self.witnesses):
            wit_id = wit.id
            self.witness_inds_by_id[wit_id] = i

    def get_byz_witnesses(self, xml: et.Element):
        """Given a VMR XML segment element (that is assumed to have been modified by the cleanup_witness_lists method), 
        returns a list of Byzantine witness sigla that do not appear in any reading.
        The output list can be used as a replacement pattern for the "Byz" siglum in a variation unit.

        Args:
            xml: A VMR XML segment element with normalized witness lists.

        Returns:
            A list of witnesses included under the "Byz" siglum
            that are not listed in the witness list of any segmentReading in the input segment element.
        """
        covered_witnesses = set()
        # Proceed for each reading in the segment:
        for segment_reading in xml.xpath(".//segmentReading"):
            # Split the witness sigla over spaces and proceed for each siglum:
            wits = witnesses_string.split()
            for wit in wits:
                wit_id = wit
                # If this witness siglum is the "Byz" siglum, then skip it 
                # (it is not technically a witness, as we will be replacing it with its consistuent witnesses):
                if wit_id == "Byz":
                    continue
                # Otherwise, get the base siglum and the type of the Witness corresponding to it:
                wit_id = self.get_base_manuscript_siglum(wit_id, ignored_manuscript_suffix_pattern)
                wit_ind = self.witness_inds_by_id[wit_id]
                wit_type = self.witnesses[wit_ind].type
                # If it is a (Greek) manuscript, then add it to the list of covered witnesses:
                if wit_type in ["papyrus", "majuscule", "minuscule", "lectionary"]:
                    covered_witnesses.add(wit_id)
        return [wit for wit in byz_witnesses if wit not in covered_witnesses]

    def parse_segments(self, xml: et.ElementTree):
        """Given a VMR XML tree representing a collation (that is assumed to have been modified by the cleanup_witness_lists method),
        parse its segments internally in this Collation.

        Args:
            xml: A VMR XML tree for a collation with normalized witness lists.
        """
        # Process each variation unit one at a time:
        for segment in xml.xpath("//segment"):
            # First, get the Byzantine witnesses for this segment:
            byz_witnesses = self.get_byz_witnesses(segment)
            # Then proceed for each reading in this segment:
            for segment_reading in segment.xpath(".//segmentReading"):
        return