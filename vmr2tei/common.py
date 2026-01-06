#!/usr/bin/env python3

from typing import List
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
    "Matt": [], # ECM Matthew data appears to expand Byz group by default
    "Mark": [
        "P84",
        "02",
        "05S",
        "011",
        "011S",
        "017",
        "022",
        "041",
        "041S",
        "042",
        "043",
        "055",
        "064",
        "099",
        "0103",
        "0104",
        "0130",
        "0167",
        "0211",
        "0233",
        "0250",
        "3",
        "4",
        "16",
        "18",
        "23",
        "26",
        "35",
        "61",
        "79",
        "105",
        "117",
        "118",
        "131",
        "152",
        "153",
        "154",
        "176",
        "178",
        "179",
        "184",
        "191",
        "222",
        "238",
        "261",
        "273",
        "304",
        "348",
        "349",
        "351",
        "372",
        "377",
        "382",
        "389",
        "472",
        "495",
        "513",
        "517",
        "544",
        "555",
        "569",
        "590",
        "595",
        "695",
        "697",
        "706",
        "713",
        "716",
        "719",
        "719S",
        "728",
        "733",
        "740",
        "752",
        "766",
        "780",
        "791",
        "803",
        "807",
        "827",
        "829",
        "855",
        "863",
        "872",
        "873",
        "949",
        "954",
        "954S",
        "979",
        "1009",
        "1029",
        "1047",
        "1071",
        "1082",
        "1084",
        "1084S",
        "1093",
        "1128",
        "1160",
        "1216",
        "1241",
        "1243",
        "1253",
        "1273",
        "1279",
        "1302",
        "1326",
        "1337",
        "1396",
        "1446",
        "1457",
        "1495",
        "1506",
        "1515",
        "1528",
        "1542",
        "1546",
        "1555",
        "1574",
        "1574S",
        "1579",
        "1593",
        "1645",
        "1654",
        "1675",
        "2106",
        "2148",
        "2174",
        "2200",
        "2206",
        "2411",
        "2486",
        "2487",
        "2517",
        "2537",
        "2538",
        "2606",
        "2607",
        "2666",
        "2680",
        "2726",
        "2737",
        "2738",
        "2744",
        "2766",
        "2786",
        "L60",
        "L211",
        "L387",
        "L563",
        "L770",
        "L773"
    ],
    "Luke": [],
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
    "John": [],
    "Rom": [],
    "1Cor": [],
    "2Cor": [],
    "Gal": [],
    "Eph": [],
    "Phil": [],
    "Col": [],
    "1Thess": [],
    "2Thess": [],
    "1Tim": [],
    "2Tim": [],
    "Titus": [],
    "Phlm": [],
    "Heb": [],
    "Jas": [

    ],
    "1Pet": [

    ],
    "2Pet": [

    ],
    "1John": [

    ],
    "2John": [

    ],
    "3John": [

    ],
    "Jude": [

    ],
    "Rev": []
}

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
manuscript_witness_pattern = re.compile(r"^(P|L|L:|F|T|Os)?\d+")
# papyrus_pattern = re.compile(r"^P\d+")
# majuscule_pattern = re.compile(r"^0\d+")
# minuscule_pattern = re.compile(r"^[1-9]\d*")
# lectionary_pattern = re.compile(r"^L\d+")
ignored_manuscript_suffix_pattern = re.compile(r"(\*|T|V|f|r)\d*$")
ignored_version_suffix_pattern = re.compile(r"(Mss|mss|Ms|ms|alt)$")
ignored_father_suffix_pattern = re.compile(r"(Mss|mss|Ms|ms|T|Text|V|v)$")
# all_manuscript_suffix_pattern = re.compile(r"(\*|T|V|f\d*|r\d*|C\d*|A\d*|K\d*|\-\d+)$")
corrector_suffix_pattern = re.compile(r"([CAK]\d*[a-z]*)$")
lection_suffix_pattern = re.compile(r"(\-\d+)$")
witness_with_parentheses_pattern = re.compile(r"(\S+)\(([^\(\)]*)\)")
version_start_pattern = re.compile(r"^(L|S|CPA|K|Ä|A|G|Go|Sl)(:|>|$)") # indicates the start of an evidence block for a particular version; if no colon, then the version is a singleton witness
latin_version_pattern = re.compile(r"^(VL|X|Y|K|C|A|VG|A|S|I|V|D|J|G|T|\d+)")
syriac_version_pattern = re.compile(r"^(Vˢ|Vᶜ|Vⱽ|Vᶠ|A|P|Ph|HT|HM|HA|H)(Mss|mss|Ms|ms)*")
cpa_version_pattern = re.compile(r"^(C|L)(Mss|mss|Ms|ms)*")
coptic_version_pattern = re.compile(r"^(S|B|M|F)(Mss|mss|Ms|ms)*")
slavonic_version_pattern = re.compile(r"^(Ch|E|M|O|Si|St|V)")
fehler_pattern = re.compile(r"f\d*$")
defective_reading_label_pattern = re.compile(r"^([a-z]+)(f\d*)$")
orthographic_reading_label_pattern = re.compile(r"^([a-z]+)(o\d*)$")

def get_base_siglum(siglum: str, ignore_patterns: List[re.Pattern] = [], keep_patterns: List[re.Pattern] = []):
    """Given a witness siglum, a list of patterns for suffixes to ignore, and a list of patterns for suffixes to keep,
    recursively remove all ignored suffixes while retaining the kept suffixes.
    The resulting base siglum is returned.
    The suffix regex defaults to the common module's manuscript_suffix_pattern.

    Args:
        siglum: A witness siglum potentially consisting of multiple suffixes that can be stripped from the base witness (e.g., "01*f").
        ignore_patterns: A list of regular expression patterns describing suffixes to remove from the siglum.
        keep_patterns: A list of regular expression patterns describing suffixes to keep in the siglum.

    Returns:
        A string representing the base siglum stripped of ignored suffixes but not kept suffixes.
    """
    base_siglum = siglum
    # First, check if this siglum contains any of the ignored suffixes:
    for pattern in ignore_patterns:
        if pattern.search(base_siglum):
            # If it does, then strip the suffix and recursively process the remainder of the siglum:
            suffix = pattern.search(base_siglum).group()
            base_siglum = base_siglum[:-len(suffix)]
            return get_base_siglum(base_siglum, ignore_patterns, keep_patterns)
    # Second, check if this siglum contains any of the kept suffixes:
    for pattern in keep_patterns:
        if pattern.search(base_siglum):
            # If it does, then strip the suffix, recursively process the remainder of the siglum,
            # and append the stripped suffix back onto the end of the output:
            suffix = pattern.search(base_siglum).group()
            base_siglum = base_siglum[:-len(suffix)]
            return (get_base_siglum(base_siglum, ignore_patterns, keep_patterns) + suffix)
    # If we get here, then the current siglum has none of the specified suffixes; return it as-is:
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
                elif version_prefix == "CPA":
                    versional_witness_regex = cpa_version_pattern
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

"""
Key function for sorting manuscript sigla.
A siglum's key is a tuple with 8 elements:
(1) the class of the witness (papyrus, majuscule, minuscule, lectionary);
(2) the number of the witness within that class;
(3) whether or not this witness is a supplement;
(4) the string associated with the supplement, if any;
(3) whether or not this witness is a lection;
(4) the string associated with the lection, if any;
(5) the type of suffix, if any, for the witness (corrector, alternate, lection, supplement); and
(6) the string associated with the suffix, if any (e.g., for 01C2b, this is "2b").
"""
def manuscript_siglum_key(wit):
    wit_string = wit.strip("*").replace("ᴷ", "")
    wit_class = 0
    wit_number = 0
    wit_supplement_class = 0
    wit_supplement_string = ""
    wit_lection_class = 0
    wit_lection_string = ""
    wit_suffix_class = 0
    wit_suffix_string = ""
    # First, if this witness has a suffix, set its suffix class and strings appropriately,
    # and then strip the suffix from the portion of the string to be processed:
    if "C" in wit_string:
        wit_suffix_class = 1
        wit_suffix_string = wit_string.split("C")[1]
        wit_suffix_string = "999" if wit_suffix_string == "" else wit_suffix_string # to ensure that the bare corrector suffix "C" follows all numbered corrector sigla
        wit_string = wit_string.split("C")[0]
    elif "A" in wit_string:
        wit_suffix_class = 2
        wit_suffix_string = wit_string.split("A")[1]
        wit_suffix_string = "999" if wit_suffix_string == "" else wit_suffix_string # to ensure that the bare alternate suffix "A" follows all numbered corrector sigla
        wit_string = wit_string.split("A")[0]
    elif "K" in wit_string:
        wit_suffix_class = 3
        wit_suffix_string = wit_string.split("K")[1]
        wit_suffix_string = "999" if wit_suffix_string == "" else wit_suffix_string # to ensure that the bare alternate suffix "K" follows all numbered corrector sigla
        wit_string = wit_string.split("K")[0]
    # Next, if this witness has a lection, set its lection class and strings appropriately,
    # and then strip the lection from the portion of the string to be processed:
    if "-" in wit_string:
        wit_lection_class = 1
        wit_lection_string = wit_string.split("-")[1]
        wit_string = wit_string.split("-")[0]
    # Next, if this witness has a supplement, set its supplement class and strings appropriately,
    # and then strip the supplement from the portion of the string to be processed:
    if "S" in wit_string:
        wit_supplement_class = 1
        wit_supplement_string = wit_string.split("S")[1]
        wit_string = wit_string.split("S")[0]
    # Finally, get the class and number of the base witness:
    if wit_string[0] == 'P':
        wit_class = 0
        wit_number = int(wit_string[1:])
    elif wit_string[0] == '0':
        wit_class = 1
        wit_number = int(wit_string[1:])
    elif wit_string[0] == 'L':
        wit_class = 3
        wit_number = int(wit_string[1:])
    else:
        wit_class = 2
        wit_number = int(wit_string)
    # Then return a tuple containing these values:
    siglum_key = (wit_class, wit_number, wit_supplement_class, wit_supplement_string, wit_lection_class, wit_lection_string, wit_suffix_class, wit_suffix_string)
    return siglum_key