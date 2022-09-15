#!/usr/bin/env python3

import time # to time calculations for users
import re # for parsing augmented witness sigla
from lxml import etree as et # for reading VMR XML inputs and writing TEI XML output
import urllib.request # for making HTTP requests to the VMR API
import numpy as np # matrix support

from common import * # import variables from the common support 
from witness import Witness

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
        self.singular_to_subreading = singular_to_subreading # flag indicating whether or not to use type="subreading" for readings with singular support
        self.verbose = verbose # flag indicating whether or not to print timing and debugging details for the user

    """
    Given a manuscript witness siglum and a regex of suffixes to remove from it,
    returns the base siglum of the witness, stripped of all suffixes described by the regex.
    The suffix regex defaults to the common module's manuscript_suffix_pattern.
    """
    def get_base_manuscript_siglum(self, siglum: str, regex: re.Pattern = all_manuscript_suffix_pattern):
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
    
    """
    Given an XML ElementTree, populate this Collation's witnesses list using the witnesses cited in XML's variant reading elements.
    """
    def parse_witnesses(self, xml: et.ElementTree):
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
        # Then proceed for each variation unit (encoded as a segment element):
        for segment in xml.xpath("//segment"):
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
                # Remove the "Byz" siglum (it can be ignored for now, since we've already added all of its witnesses to the list):
                witnesses_string = witnesses_string.replace("Byz", "")
                # Now split the witness sigla over spaces and proceed for each siglum:
                wits = witnesses_string.split()
                wit_id = ""
                wit_type = None
                for wit in wits:
                    # If this witness siglum already corresponds to an existing witness, then skip it:
                    if wit in self.witness_inds_by_id:
                        continue
                    # First, check if this siglum is for a manuscript:
                    if papyrus_pattern.match(wit):
                        wit_type = "papyrus"
                        wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    elif majuscule_pattern.match(wit):
                        wit_type = "majuscule"
                        wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    elif minuscule_pattern.match(wit):
                        wit_type = "minuscule"
                        wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    elif lectionary_pattern.match(wit):
                        wit_type = "lectionary"
                        wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                    # If not, is it a versional witness? (All of them should be normalized to have the versional prefix pattern.)
                    elif version_start_pattern.match(wit):
                        wit_type = "version"
                        wit_id = wit
                        # If this witness looks like a manuscript, then strip any ignored manuscript suffixes from it:
                        if manuscript_witness_pattern.match(wit):
                            wit_id = self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                        # TODO: Ideally, the situation below should result in all copies of the version's sigla in this unit being moved to an ambiguous reading,
                        # but this is better handled in the preparation of the data than in the parsing.
                        # If this witness ends with "ms" or "mss", then its testimony is divided here; treat it as lacunose:
                        if wit_id.endswith("ms") or wit_id.endswith("mss"):
                            continue
                    # If none of these patterns matches, then assume the witness siglum is for a father and use it as-is:
                    else:
                        wit_type = "father"
                        wit_id = wit
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
                    if manuscript_witness_pattern.match(wit) and corrector_pattern.search(wit):
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

    """

    """
    def parse_segments(self, xml: et.ElementTree):
        return