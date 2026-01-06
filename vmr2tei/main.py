from typing import List  # for list-like inputs
from pathlib import Path  # for validating file address inputs
import time # to delay requests
from tqdm import tqdm # for progress bar
from lxml import etree as et  # for parsing XML input
import urllib.request # for making HTTP requests to the VMR API
import typer # for parsing command-line input

from .collation import Collation

app = typer.Typer(rich_markup_mode="rich")

"""
Given a book abbreviation, populate a list of how many verses are in each chapter of that book.
"""
def get_verse_metadata(book: str):
    verse_metadata = []
    print(f"Requesting versification metadata for {book}...")
    try:
        # Request metadata for the book in question:
        request_str = f"https://ntvmr.uni-muenster.de/community/vmr/api/metadata/v11n/get/?detail=chapter&subset={book}&format=xml"
        # Parse the contents of the HTTP request as an XML string:
        xml = None
        with urllib.request.urlopen(request_str) as r:
            contents = r.read()
            xml = et.fromstring(contents)
        # Then retrieve the number of chapters in this book:
        for chapter in xml.xpath(".//chapter"):
            verse_metadata.append(int(chapter.get("verseMax")))
    except Exception as err:
        print(f"Error requesting versification metadata for book {book}: {err}")
        exit(1)
    return verse_metadata

"""
Populate a list of manuscript elements from the VMR's Liste API.
"""
def get_manuscripts_xml():
    manuscripts_xml = None
    print(f"Requesting manuscript data from VMR Liste API...")
    try:
        # Request metadata for witnesses whose document IDs are in the range for regular manuscripts:
        request_str = f"https://ntvmr.uni-muenster.de/community/vmr/api/metadata/liste/search/?docID=0-49999&detail=document"
        # Parse the contents of the HTTP request as an XML string:
        with urllib.request.urlopen(request_str) as r:
            contents = r.read()
            manuscripts_xml = et.fromstring(contents)
    except Exception as err:
        print(f"Error requesting manuscript data: {err}")
        exit(1)
    return manuscripts_xml

"""
Populate a VMR XML-encoded list of hardcoded versional witnesses.
TODO: The VMR Liste API currently does not assign dates to these witnesses, and its data for them is not well-organized,
so it is best to use a hardcoded list first.
"""
def get_versions_xml():
    versions_xml = None
    print(f"Generating hardcoded versional data VMR XML element...")
    versions_xml = et.fromstring("""
    <manuscripts>
        <manuscript docID="91104" primaryName="L:VL" gaNum="L:VL" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="lat"/>
        <manuscript docID="91002" primaryName="L:X" gaNum="L:X" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91005" primaryName="L:Y" gaNum="L:Y" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91008" primaryName="L:K" gaNum="L:K" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91011" primaryName="L:C" gaNum="L:C" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91107" primaryName="L:VG" gaNum="L:VG" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="lat"/>
        <manuscript docID="91014" primaryName="L:A" gaNum="L:A" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91017" primaryName="L:S" gaNum="L:S" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91020" primaryName="L:I" gaNum="L:I" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91023" primaryName="L:V" gaNum="L:V" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91026" primaryName="L:D" gaNum="L:D" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91074" primaryName="L:J" gaNum="L:J" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91077" primaryName="L:G" gaNum="L:G" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91080" primaryName="L:T" gaNum="L:T" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="la"/>
        <manuscript docID="91030" primaryName="K:S" gaNum="K:S" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="cop-sa"/>
        <manuscript docID="91033" primaryName="K:B" gaNum="K:B" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="cop-bo"/>
        <manuscript docID="91036" primaryName="K:F" gaNum="K:F" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="cop-fa"/>
        <manuscript docID="91083" primaryName="K:M" gaNum="K:M" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="cop-mae"/>
        <manuscript docID="91087" primaryName="S:Vᶜ" gaNum="S:Vᶜ" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91088" primaryName="S:Vˢ" gaNum="S:Vˢ" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91089" primaryName="S:Vᶠ" gaNum="S:Vᶠ" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91128" primaryName="S:Vⱽ" gaNum="S:Vⱽ" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91090" primaryName="S:P" gaNum="S:P" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91038" primaryName="S:H" gaNum="S:H" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91045" primaryName="S:HT" gaNum="S:HT" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91041" primaryName="S:HA" gaNum="S:HA" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91047" primaryName="S:HM" gaNum="S:HM" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91049" primaryName="S:Ph" gaNum="S:Ph" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91050" primaryName="Ä:Ä" gaNum="Ä:Ä" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="Ethi"/>
        <manuscript docID="91094" primaryName="CPA:C" gaNum="CPA:C" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91097" primaryName="CPA:L" gaNum="CPA:L" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="syc"/>
        <manuscript docID="91101" primaryName="Go:Go" gaNum="Go:Go" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="got"/>
        <manuscript docID="91056" primaryName="G" gaNum="G" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="ka"/>
        <manuscript docID="91059" primaryName="Sl" gaNum="Sl" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="cu"/>
        <manuscript docID="91066" primaryName="Ar:S" gaNum="Ar:S" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="ar"/>
        <manuscript docID="91073" primaryName="Ar:Smg" gaNum="Ar:Smg" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="ar"/>
        <manuscript docID="91067" primaryName="Ar:E" gaNum="Ar:E" v11n="" orig="" origEarly="0" origLate="0" userID="" groupID="" lang="ar"/>
    </manuscripts>
    """)
    return versions_xml

"""
Populate a list of patristic witnesses from the VMR's Liste API.
"""
def get_fathers_xml():
    fathers_xml = None
    print(f"Requesting patristic data from VMR Liste API...")
    try:
        # Request metadata for witnesses whose document IDs are in the range for patristic witnesses:
        request_str = f"https://ntvmr.uni-muenster.de/community/vmr/api/metadata/liste/search/?docID=91500-91623|91625-91671&detail=document" # we skip docID 91624, as this is a duplicate of ProclC
        # Parse the contents of the HTTP request as an XML string:
        with urllib.request.urlopen(request_str) as r:
            contents = r.read()
            fathers_xml = et.fromstring(contents)
    except Exception as err:
        print(f"Error requesting manuscript data: {err}")
        exit(1)
    return fathers_xml

@app.command()
def convert(
    include_a: bool = typer.Option(False, help="If specified, include the Ausgangstext witness (A) in the collation. Split-line readings will be treated as ambiguous readings for this witness."),
    verbose: bool = typer.Option(False, help="Enable verbose logging (mostly for debugging purposes)."),
    book: str = typer.Argument(
        ...,
        help="The abbreviation for the book whose ECM collation from the New Testament Virtual Manuscript Room (NTVMR) is desired (e.g., Matt, Mark, Acts).",
    ),
    output: Path = typer.Argument(
        ...,
        exists=False,
        file_okay=True,
        dir_okay=False,
        writable=True,
        readable=False,
        resolve_path=True,
        help="Filename for output TEI XML collation. The output must have the file extension .xml.",
    ),
):
    # Make sure the output is an XML file:
    if output.suffix.lower() != ".xml":
        print("Error with output file: The output file is not an XML file. Make sure the output file type is .xml.")
    # First, populate a list of verses for every chapter of the specified book:
    verse_metadata = get_verse_metadata(book)
    # Then initialize a collation and populate its witness list with the witness XML data:
    coll = Collation(book, include_a, verbose)
    # Then add manuscripts from the VMR's Liste API to the collation's witness list:
    manuscripts_xml = get_manuscripts_xml()
    coll.add_witnesses(manuscripts_xml)
    # Then add versional witnesses from a hardcoded VMR XML element:
    versions_xml = get_versions_xml()
    coll.add_witnesses(versions_xml)
    # Then add patristic witnesses from the VMR's Liste API to the collation's witness list:
    fathers_xml = get_fathers_xml()
    coll.add_witnesses(fathers_xml)
    # Then try to query the VMR API for the collation data:
    print(f"Requesting collation data for book {book}...")
    with tqdm(total=sum(verse_metadata)) as pbar:
        # Initialize the base request URL based on specified arguments:
        base_request_str = f"https://ntvmr.uni-muenster.de/community/vmr/api/variant/apparatus/get/?format=xml&positiveConversion=true&cleanHands=true&includeCitations=true"
        # Proceed for each chapter in the book:
        for i in range(len(verse_metadata)):
            # Proceed for each verse in the chapter:
            for j in range(verse_metadata[i]):
                # Generate the verse index for the current verse:
                index = f"{book}.{i+1}.{j+1}"
                request_str = base_request_str + f"&indexContent={index}"
                # Parse the contents of the HTTP request as an XML string:
                verse_collation_xml = None
                try:
                    with urllib.request.urlopen(request_str) as r:
                        if verbose:
                            print(f"Requesting collation data for {index}...")
                        contents = r.read()
                        verse_collation_xml = et.fromstring(contents)
                except Exception as err:
                    print(f"Error requesting ECM collation data for index {index}: {err}")
                # If this verse has no collation data, then notify the user and move on:
                if verse_collation_xml is None:
                    print(f"WARNING: Request for {index} returned an empty response! Skipping this verse...")
                    continue
                for segment_xml in verse_collation_xml.xpath(".//segment"):
                    coll.add_segment(segment_xml)
                pbar.update(1)
                time.sleep(1) # per Troy Griffitts's request, wait one second between each request to allow others to use the system
    # Next, postprocess the witness lists of the collation:
    print(f"Post-processing witness lists in collation...")
    coll.postprocess_witness_lists()
    # Finally, write the internal state of the Collation to a TEI XML output:
    tei_xml = coll.to_xml()
    tei_xml.write(output, doctype='<!DOCTYPE TEI>', encoding='utf-8', xml_declaration=True, pretty_print=True)