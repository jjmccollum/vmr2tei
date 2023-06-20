#!/usr/bin/env python3

import re
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
ECM Byzantine witnesses by book
"""
byz_witnesses_by_book = {
    "Mark": [
        # TODO: need access to ECM Mark's Codices Byzantini list
    ],
    "Acts": [
        "P57",
        "014",
        "014S",
        "020",
        "025",
        "049",
        "077",
        "0120", 
        "0142",
        "0166",
        "0294",
        "1",
        "6",
        "18",
        "35",
        "43",
        "69",
        "93",
        "103",
        "104",
        "206S",
        "218",
        "228",
        "254",
        "319",
        "321",
        "323",
        "326",
        "330",
        "365",
        "378",
        "383",
        "424",
        "459",
        "468",
        "607",
        "617",
        "642",
        "665",
        "808",
        "876",
        "886",
        "1003",
        "1127",
        "1241",
        "1243",
        "1251",
        "1359",
        "1448",
        "1509",
        "1563",
        "1609",
        "1718",
        "1735",
        "1739S",
        "1827S",
        "1832",
        "1837",
        "1852",
        "1874",
        "1874S",
        "1890S1",
        "1890S2",
        "2243",
        "2374",
        "2570",
        "2774",
        "L23",
        "L156",
        "L587",
        "L809",
        "L1178",
    ],
    "Jas": [

    ],
    "1Pet": [

    ],
    "2Pet": [

    ],
    "1Jn": [

    ],
    "2Jn": [

    ],
    "3Jn": [

    ],
    "Jude": [

    ],
}

"""
Versional witness prefixes
"""
version_prefixes = [
    "L",
    "S",
    "K",
    "Ä",
    "A",
    "G",
    "Sl",
]

"""
Hardcoded settings based on VMR XML conventions
"""
omission_string = "om."
overlap_label = "zu"
unclear_label = "zv"
ambiguous_label = "zw"
lac_label = "zz"

"""
Regular expressions
"""
greek_rdg_pattern = re.compile(r"[\u03b1-\u03c9]")
latin_rdg_pattern = re.compile(r"[\u0061-\u007a]")
syriac_rdg_pattern = re.compile(r"[\u0710-\u074f]")
coptic_rdg_pattern = re.compile(r"[\u03e2-\u03ef\u2c80-\u2cee]")
manuscript_witness_pattern = re.compile(r"^(P|L|L:)?\d+")
papyrus_pattern = re.compile(r"^P\d+")
majuscule_pattern = re.compile(r"^0\d+")
minuscule_pattern = re.compile(r"^[1-9]\d*")
lectionary_pattern = re.compile(r"^L\d+")
corrector_pattern = re.compile(r"[CAK]\d*")
firsthand_corrector_pattern = re.compile(r"\*V*C\d*")
ignored_manuscript_suffix_pattern = re.compile(r"(\*|T|V|f)\d*$")
ignored_version_suffix_pattern = re.compile(r"(Mss|mss|Ms|ms)$")
ignored_father_suffix_pattern = re.compile(r"(Mss|mss|Ms|ms|T|Text|V|v)$")
all_manuscript_suffix_pattern = re.compile(r"(\*|T|V|f\d*|C\d*|A\d*|K\d*|L\d+)$")
witness_with_parentheses_pattern = re.compile(r"(\S+)\(([^\(\)]*)\)")
version_start_pattern = re.compile(r"^(L|S|K|Ä|A|G|Sl)(:|>|$)") # indicates the start of an evidence block for a particular version; if no colon, then the version is a singleton witness
latin_version_pattern = re.compile(r"^(V|AU|HIL|QU|\d+)")
syriac_version_pattern = re.compile(r"^(A|P|HT|HM|HA|H)(Mss|mss|Ms|ms)*")
coptic_version_pattern = re.compile(r"^(S|B|M|F)(Mss|mss|Ms|ms)*")
slavonic_version_pattern = re.compile(r"^(Ch|E|M|O|Si|St|V)")
fehler_pattern = re.compile(r"f\d*$")
defective_reading_label_pattern = re.compile(r"^[a-z]+f\d*$")
orthographic_reading_label_pattern = re.compile(r"^[a-z]+o\d*$")

def get_base_siglum(siglum: str, regex: re.Pattern = all_manuscript_suffix_pattern):
    """Given a witness siglum and a regex of suffixes to remove from it,
    strips all suffixes described by the regex from the siglum until no further suffixes can be found.
    The resulting base siglum is returned.
    The suffix regex defaults to the common module's manuscript_suffix_pattern.

    Args:
        siglum: A witness siglum potentially consisting of multiple suffixes that can be stripped from the base witness (e.g., "01*f").
        regex: A regular expression pattern to identify unwanted suffixes from the siglum.

    Returns:
        A string representing the base siglum stripped of unwanted suffixes.
    """
    base_siglum = siglum
    suffix_found = True
    while (suffix_found):
        suffix_found = False
        # Otherwise, check if it has a suffix to be removed, and remove the suffix if so:
        if regex.search(base_siglum):
            suffix_found = True
            suffix = regex.search(base_siglum).group()
            base_siglum = base_siglum[:-len(suffix)]
    return base_siglum

def split_versional_witnesses(siglum: str, regex: re.Pattern):
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

def expand_parenthetical_suffixes(wit_str: str):
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
        # If we haven't entered the versional evidence block, then leave any entries that do not match the pattern of a versional evidence block unchanged:
        if version_prefix == "" and not version_start_pattern.search(wit):
            old_versional_sigla.append(wit)
            normalized_versional_sigla.append(wit)
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
                old_sigla = split_versional_witnesses(version_suffix, versional_witness_regex)
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
    normalized_versional_sigla_str = " ".join(normalized_versional_sigla)
    return normalized_versional_sigla_str