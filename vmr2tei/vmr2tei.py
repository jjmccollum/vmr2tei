#!/usr/bin/env python3

import time # to time calculations for users
import re # for parsing augmented witness sigla
from lxml import etree as et # for reading VMR XML inputs and writing TEI XML output
import urllib.request # for making HTTP requests to the VMR API
import numpy as np # matrix support

from common import * # import variables from the common support 
from witness import Witness

"""
Base class for reading collation data and reformatting it as a matrix according to customizable rules.
"""
class CollationParser():
    """
	Constructs a new CollationParser with the given settings.
	"""
    def __init__(self, verbose: bool = False):
        self.witnesses = [] # internal list of Witness instances
        self.witness_inds_by_id = {} # internal dictionary mapping witness IDs to their indices in the list
        self.verbose = verbose # flag indicating whether or not to print timing and debugging details for the user

    """
    Given a string of witness sigla, expand any base sigla followed by one or more suffixes in the same parentheses to the same sigla followed by each suffix
    """
    def expand_parenthetical_suffixes(self, wit_str: str):
        expanded_wit_str = wit_str
        witness_with_parentheses_pattern = re.compile(r"(\S+)\(([^\(\)]*)\)")
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

    """
    Given a manuscript witness siglum and a regex of suffixes to remove from it,
    returns the base siglum of the witness, stripped of all suffixes described by the regex.
    The suffix regex defaults to the common module's manuscript_suffix_pattern.
    """
    def get_base_manuscript_siglum(self, siglum: str, regex: re.Pattern = manuscript_suffix_pattern):
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
    Given an XML ElementTree, populate this CollationParser's witnesses list using the witnesses cited in XML's variant reading elements.
    """
    def read_witnesses(self, xml: et.ElementTree):
        # Start by adding the Byzantine witnesses to the witness list:

        # Then proceed for each variation unit (encoded as a segment element):
        for segment in xml.xpath("//segment"):
            # Add the remaining witnesses listed for all readings to the internal witness list:
            for segment_reading in xml.xpath(".//segmentReading"):
                # Get its label:
                rdg_label = segment_reading.get("label")
                # Get its witness string:
                witnesses_string = segment_reading.get("witnesses")
                # Remove the "Byz" siglum (it can be ignored for now, since we've added all of its witnesses to the list):
                witnesses_string = witnesses_string.replace("Byz", "")
                # Remove any square brackets around witnesses:
                witnesses_string = witnesses_string.replace("[", "").replace("]", "")
                # Replace any right angle brackets with spaces:
                witnesses_string = witnesses_string.replace(">", " ")
                # Expand out any parenthetical suffixes in the witness string:
                witnesses_string = self.expand_parenthetical_suffixes(witnesses_string)
                wits = witnesses_string.split()
                wit_id = ""
                wit_type = None
                version_prefix = ""
                for wit in wits:
                    # Is this the start of a versional block?
                    if version_start_pattern.match(wit):
                        # Then set the current witness type to "version":
                        wit_type = "version"
                        # If this siglum contains a colon, the the part before the colon is the new version prefix and should be saved for later,
                        # and the entire siglum is already correctly formatted:
                        if ":" in wit:
                            version_prefix = wit.split(":")[0] + ":"
                            wit_id = wit
                        # Otherwise, treat the siglum as a singleton versional siglum and add it to the list:
                        else:
                            wit_id = wit
                    # Otherwise, are we already processing versional witnesses?
                    elif wit_type == "version":
                        # By default, the witness siglum should have the current version's prefix prepended to it:
                        wit_id = version_prefix + wit
                        # If this siglum looks like minuscule manuscript siglum, then it is an Old Latin manuscript; 
                        # check for any corrector sigla and strip any suffixes ignored for manuscripts:
                        if minuscule_pattern.match(wit):
                            wit_id = version_prefix + self.get_base_manuscript_siglum(wit, ignored_manuscript_suffix_pattern) # strip any ignored suffixes
                        continue
                    # Otherwise, we haven't gotten to versions yet; check if this siglum is for a manuscript:
                    elif papyrus_pattern.match(wit):
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
                    # If none of these patterns matches, then assume the witness siglum is for a father and use it as-is:
                    else:
                        wit_type = "father"
                        wit_id = wit
                    # If this witness looks like a manuscript and has a corrector suffix, then use the "corrector" type instead:
                    if manuscript_witness_pattern.match(wit) and corrector_pattern.search(wit):
                        if wit_id not in self.witness_inds_by_id:
                            witness = Witness(wit_id, "corrector")
                            self.witnesses.append(witness)
                            self.witness_inds_by_id[wit_id] = len(self.witnesses) - 1
                    # Otherwise, check if a Witness with this siglum has already been added, and add a new Witness if not:
                    else:
                        if wit_id not in self.witness_inds_by_id:
                            witness = Witness(wit_id, wit_type)
                            self.witnesses.append(witness)
                            self.witness_inds_by_id[wit_id] = len(self.witnesses) - 1