#!/usr/bin/env python3

from lxml import etree as et

from common import tei_ns


class Witness:
    """Base class for storing TEI XML witness data internally.

    This corresponds to a witness element in the collation.

    Attributes:
        n: The number or ID string of this Witness.
        type: A string representing the type of witness. Examples include "papyrus", "minuscule", "majuscule", "corrector", "version", and "father".
    """

    def __init__(self, id: str, witness_type: str = None, verbose: bool = False):
        """Constructs a new Witness instance from the TEI XML input.

        Args:
            id: A string representing this witness's ID.
            type: A string representing the type of witness. Examples include "papyrus", "minuscule", "majuscule", "corrector", "version", and "father".
            verbose: An optional flag indicating whether or not to print status updates.
        """
        self.id = id
        self.type = witness_type
        if verbose:
            print("New Witness %s with type %s" % (self.id, self.type))

    def to_xml(self):
        """Returns a witness TEI XML element constructed from this Witness.

        Returns:
            An XML element with attributes matching those of this Witness.
        """
        xml = et.Element("witness", nsmap={None: tei_ns})
        xml.set("n", self.id)
        xml.set("type", self.type)
        return xml