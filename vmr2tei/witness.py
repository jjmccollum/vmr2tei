#!/usr/bin/env python3

from lxml import etree as et # for reading TEI XML inputs

from .common import *


class Witness:
    """Base class for storing TEI XML witness data internally.

    This corresponds to a witness element in the collation.

    Attributes:
        id: The number or ID string of this Witness.
        type: A string representing the type of witness. Examples include "papyrus", "minuscule", "majuscule", "corrector", "version", and "father".
        date_range: A list containing a minimum date and a maximum date for the origin of this witness.
    """

    def __init__(self, _id: str, _type: str = None, _min_date: int = None, _max_date: int = None, verbose: bool = False):
        """Constructs a new Witness instance with the specified fields."""
        self.id = _id
        self.type = _type
        self.date_range = [_min_date, _max_date]
        if verbose:
            print(f"New Witness (id: {self.id}, type: {self.type})")

    @classmethod
    def from_xml(cls, xml: et.Element, verbose: bool = False):
        """Constructs a new Witness instance from a VMR XML manuscript element.

        Args:
            xml: A VMR XML manuscript element representing this witness.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        _id = xml.get("gaNum")
        # Determine the type of this witness based on its docID:
        _type = None
        doc_id = int(xml.get("docID"))
        if doc_id >= 10000 and doc_id < 50000:
            _type = None
        elif doc_id >= 50000 and doc_id < 80000:
            # Apostolic fathers manuscripts
            _type = "father"
        elif doc_id >= 80000 and doc_id < 91500:
            # Versions
            _type = "version"
        elif doc_id >= 91500 and doc_id < 92000:
            # Fathers
            _type = "father"
        elif doc_id >= 100000 and doc_id < 200000:
            # "Var" manuscripts
            _type = None
        elif doc_id >= 200000 and doc_id < 300000:
            # Vetus Latina manuscripts
            _type = None
        elif doc_id >= 510000 and doc_id < 520000:
            # T witnesses
            _type = None
        elif doc_id >= 520000 and doc_id < 530000:
            # Ostraca
            _type = None
        elif doc_id >= 602000 and doc_id < 700000:
            # Coptic manuscripts
            _type = None
        elif doc_id >= 700000 and doc_id < 720000:
            # Syriac manuscripts
            _type = None
        elif doc_id >= 720000 and doc_id < 800000:
            # Christian Palestinian Aramaic manuscripts
            _type = None
        elif doc_id >= 900000 and doc_id < 910000:
            # Arabic manuscripts
            _type = None
        elif doc_id >= 910000 and doc_id < 920000:
            # Armenian manuscripts
            _type = None
        elif doc_id >= 920000 and doc_id < 930000:
            # Ethiopic manuscripts
            _type = None
        elif doc_id >= 930000 and doc_id < 940000:
            # Slavonic manuscripts
            _type = None
        elif doc_id >= 940000 and doc_id < 941000:
            # Gothic manuscripts
            _type = None
        elif doc_id >= 941000 and doc_id < 950000:
            # Georgian manuscripts
            _type = None
        elif doc_id >= 1000000 and doc_id < 8000000:
            # Critical editions
            _type = "edition"
        _min_date = int(xml.get("origEarly")) if xml.get("origEarly") is not None else None
        _max_date = int(xml.get("origLate")) if xml.get("origLate") is not None else None
        # If both the minimum and maximum date are det to 0, then treat them as null:
        if _min_date == 0 and _max_date == 0:
            _min_date = None
            _max_date = None
        return cls(_id, _type, _min_date, _max_date, verbose)        

    def to_xml(self):
        """Returns a witness TEI XML element constructed from this Witness.

        Returns:
            An XML Element with attributes matching those of this Witness.
        """
        xml = et.Element("{%s}witness" % tei_ns)
        xml.set("n", self.id)
        if self.type is not None: 
            xml.set("type", self.type)
        # If either end of this witness's date range is non-null, then add an origDate element under the witness element:
        if self.date_range[0] is not None or self.date_range[1] is not None:
            orig_date = et.Element("{%s}origDate" % tei_ns)
            if self.date_range[0] is not None and self.date_range[1] is not None:
                if self.date_range[0] == self.date_range[1]:
                    orig_date.set("when", str(self.date_range[0]))
                else:
                    orig_date.set("notBefore", str(self.date_range[0]))
                    orig_date.set("notAfter", str(self.date_range[1]))
            elif self.date_range[0] is not None:
                orig_date.set("notBefore", str(self.date_range[0]))
            else:
                orig_date.set("notAfter", str(self.date_range[1]))
            xml.append(orig_date)
        return xml