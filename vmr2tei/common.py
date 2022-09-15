#!/usr/bin/env python3

import re

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
ECM Byzantine witnesses (in Acts)
"""
byz_witnesses = []

"""
Hardcoded settings based on VMR XML conventions
"""
omission_string = "om."
overlap_label = "zu"
ambiguous_label = "zw"
lac_label = "zz"

"""
Regular expressions
"""
greek_re = re.compile(r"[\u03b1-\u03c9]")
latin_re = re.compile(r"[\u0061-\u007a]")
syriac_re = re.compile(r"[\u0710-\u074f]")
coptic_re = re.compile(r"[\u03e2-\u03ef\u2c80-\u2cee]")
manuscript_witness_pattern = re.compile(r"^(P|L|L:)?\d+")
papyrus_pattern = re.compile(r"^P\d+")
majuscule_pattern = re.compile(r"^0\d+")
minuscule_pattern = re.compile(r"^[1-9]\d*")
lectionary_pattern = re.compile(r"^L\d+")
corrector_pattern = re.compile(r"[CAK]\d+")
ignored_manuscript_suffix_pattern = re.compile(r"(\*|T|V|f\d*)$")
all_manuscript_suffix_pattern = re.compile(r"(\*|T|V|f\d*|C\d*|A\d*|K\d*|/\d+)$")
version_start_pattern = re.compile(r"^(L|S|K|Ä|A|G|Sl)(:|>|$)") # indicates the start of an evidence block for a particular version; if no colon, then the version is a singleton witness
fehler_pattern = re.compile(r"f\d*$")
defective_reading_label_pattern = re.compile(r"^[a-z]+f\d*$")
orthographic_reading_label_pattern = re.compile(r"^[a-z]+o\d*$")
