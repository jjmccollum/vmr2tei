#!/usr/bin/env python3

import time # to time calculations for users
from lxml import etree as et # for reading TEI XML inputs

from .common import *


class Witness:
    """Base class for storing TEI XML witness data internally.

    This corresponds to a witness element in the collation.

    Attributes:
        n: The number or ID string of this Witness.
        type: A string representing the type of witness. Examples include "papyrus", "minuscule", "majuscule", "corrector", "version", and "father".
        key: A tuple representing the sort key of this Witness.
    """

    def __init__(self, id: str, witness_type: str = None, verbose: bool = False):
        """Constructs a new Witness instance from the TEI XML input.

        Args:
            id: A string representing this witness's ID.
            type: A string representing the type of witness. Examples include "papyrus", "minuscule", "majuscule", "corrector", "version", and "father".
            verbose: An optional flag indicating whether or not to print status updates.
        """
        t0 = time.time()
        self.id = id
        self.type = witness_type
        self.key = self.get_key()
        t1 = time.time()
        if verbose:
            print(f"New Witness (id: {self.id}, type: {self.type}) constructed in {(t1 - t0):0.4f}s.")

    def __lt__(self, other):
        return self.key < other.key

    def __gt__(self, other):
        return self.key > other.key

    def __eq__(self, other):
        return self.key == other.key

    def get_key(self):
        """Returns a tuple representing the sort key for this Witness.

        Return: A tuple whose first entry reflects the type of this witness (with correctors being classified with the types of their base sigla),
        whose second entry reflects the numerical index of this witness (or a high number if it has no numerical index),
        and whose third entry is the remaining string left over after these first two components of the witness siglum are removed.
        """
        wit_id = self.id
        wit_type = self.type
        key_list = []
        # If the type is unspecified or "corrector", then infer the type to use for the key from the ID:
        if wit_type is None or wit_type == "corrector":
            if papyrus_pattern.match(wit_id):
                wit_type = "papyrus"
            elif majuscule_pattern.match(wit_id):
                wit_type = "majuscule"
            elif minuscule_pattern.match(wit_id):
                wit_type = "minuscule"
            elif lectionary_pattern.match(wit_id):
                wit_type = "lectionary"
            elif version_start_pattern.match(wit_id):
                wit_type = "version"
            else:
                wit_type = "father"
        # The first sort key is based on the type of witness:
        if wit_type == "papyrus":
            key_list.append(1)
            wit_id = wit_id[1:] # remove the P prefix
        elif wit_type == "majuscule":
            key_list.append(2)
            wit_id = wit_id[1:] # remove the 0 prefix
        elif wit_type == "minuscule":
            key_list.append(3)
        elif wit_type == "lectionary":
            key_list.append(4)
            wit_id = wit_id[1:] # remove the L prefix
        elif wit_type == "version":
            version = wit_id.split(":")[0]
            wit_id = wit_id.split(":")[1]
            key_list.append(5 + version_prefixes.index(version)) # further sort versional witnesses by their language
        elif wit_type == "father":
            key_list.append(5 + len(version_prefixes))
        # The second sort key is based on the numerical index of the witness:
        if minuscule_pattern.match(wit_id):
            wit_number_str = minuscule_pattern.match(wit_id).group()
            key_list.append(int(wit_number_str))
            wit_id = wit_id[len(wit_number_str):] # remove the numerical part of the siglum
        else:
            key_list.append(10000)
        # If any part of the string remains, then use that as the last part of the sort key:
        if len(wit_id) > 0:
            key_list.append(wit_id)
        return tuple(key_list)

    def to_xml(self):
        """Returns a witness TEI XML element constructed from this Witness.

        Returns:
            An XML Element with attributes matching those of this Witness.
        """
        xml = et.Element("{%s}witness" % tei_ns)
        xml.set("n", self.id)
        xml.set("type", self.type)
        return xml