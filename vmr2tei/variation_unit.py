#!/usr/bin/env python3

from typing import List
from lxml import etree as et # for reading TEI XML inputs

from .common import *
from .reading import Reading

def get_reading_key(label: str):
    """Given a reading label, recursively populate a Tuple representing its key for sorting.
    The Tuple consists of the numerical index of the reading itself, converted from its alphabetical code,
    with similar keys appended for any defective and orthographic subvariants.

    Returns:
        A Tuple representing the sort key for this reading label.
    """
    key_list = []
    # If this label corresponds to a defective subvariation, then append keys for the defective subvariant to the keys for the reading it modifies:
    if len(re.findall(defective_reading_label_pattern, label)) > 0:
        match = re.findall(defective_reading_label_pattern, label)[0]
        # First, get the key for the base reading:
        base_reading = match[0]
        subvariant_label = match[1]
        key_list = list(get_reading_key(base_reading))
        # Then append keys for the defective subreading to this list:
        key_list.append(1)
        if len(subvariant_label.strip("f")) > 0:
            key_list.append(int(subvariant_label.strip("f")))
        return tuple(key_list)
    # If this label corresponds to an orthographic subvariation, then append keys for the orthographic subvariant to the keys for the reading it modifies:
    if len(re.findall(orthographic_reading_label_pattern, label)) > 0:
        match = re.findall(orthographic_reading_label_pattern, label)[0]
        # First, get the key for the base reading:
        base_reading = match[0]
        subvariant_label = match[1]
        key_list = list(get_reading_key(base_reading))
        # Then append keys for the orthographic subreading to this list:
        key_list.append(1)
        if len(subvariant_label.strip("o")) > 0:
            key_list.append(int(subvariant_label.strip("o")))
        return tuple(key_list)
    # Otherwise, convert the alphabetical label of the reading to a numerical index, and use a singleton list containing this index as the key:
    numerical_index = 0
    for i in range(len(label)):
        numerical_index += 26**i * (ord(label[-i-1]) - ord('a') + 1)
    key_list.append(numerical_index)
    return tuple(key_list)
    

class VariationUnit:
    """Base class for storing TEI XML variation unit data internally.

    This corresponds to an app element in the collation.

    Attributes:
        id: The ID string of this variation unit, which should be unique.
        readings: A list of Readings contained in this VariationUnit.
    """

    def __init__(self, _id: str, _readings: List[Reading], verbose: bool = False):
        """Constructs a new VariationUnit instance with the specified fields."""
        self.id = _id
        self.readings = list(_readings)
        if verbose:
            print(f"New VariationUnit (id: {self.id}, {len(self.readings)} readings)")

    @classmethod
    def from_xml(cls, xml: et.Element, include_a: bool = False, verbose: bool = False):
        """Constructs a new VariationUnit instance from a VMR XML segment element.

        Args:
            xml: A VMR XML segment element whose segmentReading children all have normalized witness lists.
            include_a: An optional flag indicating whether or not to include the Ausgangstext (A) as an additional witness in the collation. Split-line readings will be treated as ambiguous readings for this witness.
            if the reading does not already have a type and has support from at most one witness.
            verbose: An optional flag indicating whether or not to print status updates.
        """
        # Combine the segment's verse and wordsegs attributes into a single ID:
        _id = ""
        if xml.get("verse") is not None:
            _id += xml.get("verse")
            if xml.get("wordsegs") is not None:
                _id += "/" + xml.get("wordsegs")
        # Initialize its list of readings, tracking any readings that have diamonds for split lines:
        _readings = []
        split_reading_ids = []
        for segment_reading in xml.xpath(".//segmentReading"):
            rdg = Reading.from_xml(segment_reading, verbose)
            if segment_reading.get("label") is not None and "♦" in segment_reading.get("label"):
                split_reading_ids.append(rdg.id)
            _readings.append(rdg)
        # If the Ausgangstext is to be included, then determine if its attestation is split, and add it to the appropriate reading's witness list:
        if include_a:
            if len(split_reading_ids) > 0:
                # The Ausgangstext always has the first reading as one of its potential readings:
                if "a" not in split_reading_ids:
                    split_reading_ids.insert(0, "a")
                a_rdg = Reading(ambiguous_label, "ambiguous", None, ["A"], split_reading_ids)
                _readings.insert(0, a_rdg)
            else:
                _readings[0].wits.insert(0, "A")
        # Next, sort the readings:
        _readings = sorted(_readings, key = lambda reading: get_reading_key(reading.id))
        # Finally, relabel readings with duplicate IDs to ensure that they are all distinct:
        repeated_reading_ids = set()
        occurrences_by_reading_id = {}
        for reading in _readings:
            if reading.id not in occurrences_by_reading_id:
                occurrences_by_reading_id[reading.id] = 0
            occurrences_by_reading_id[reading.id] += 1
            if occurrences_by_reading_id[reading.id] > 1:
                repeated_reading_ids.add(reading.id)
        for i in range(len(_readings) - 1, -1, -1):
            reading = _readings[i]
            if reading.id in repeated_reading_ids:
                new_id = reading.id + "-" + str(occurrences_by_reading_id[reading.id])
                occurrences_by_reading_id[reading.id] -= 1
                reading.id = new_id
        return cls(_id, _readings, verbose)

    def to_xml(self):
        """Returns an app TEI XML element constructed from this VariationUnit.

        Returns:
            An XML Element with attributes matching those of this VariationUnit and child elements corresponding to its Readings.
        """
        xml = et.Element("{%s}app" % tei_ns)
        if self.id is not None:
            xml.set("n", self.id)
        for rdg in self.readings:
            xml.append(rdg.to_xml())
        return xml