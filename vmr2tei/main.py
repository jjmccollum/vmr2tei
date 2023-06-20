from typing import List  # for list-like inputs
from pathlib import Path  # for validating file address inputs
import time # to time calculations for users
from lxml import etree as et  # for parsing XML input
import urllib.request # for making HTTP requests to the VMR API
import typer # for parsing command-line input

from .collation import Collation

app = typer.Typer(rich_markup_mode="rich")

@app.command()
def convert(
    singular_to_subreading: bool = typer.Option(False, help="Classify singular readings without a type as type \"subreading\"."),
    verbose: bool = typer.Option(False, help="Enable verbose logging (mostly for debugging purposes)."),
    index: str = typer.Argument(
        ...,
        help="A content index for the ECM collation hosted in the New Testament Virtual Manuscript Room (NTVMR); e.g., Acts (for the whole book), Acts.1 or Acts.1-5 (for one or more chapters), or Acts.1.1 or Acts.1.1-5 (for one or more verses).",
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
    # Get the book name from the index:
    book = index.split(".")[0]
    # Make sure the output is an XML file:
    if output.suffix.lower() != ".xml":
        print("Error with output file: The output file is not an XML file. Make sure the output file type is .xml.")
    # If it is, then try to query the VMR API for the collation data:
    vmr_xml = None
    try:
        # Get the appropriate project name based on the book in question:
        request_str = f"https://ntvmr.uni-muenster.de/community/vmr/api/variant/apparatus/get/?indexContent={index}&positiveConversion=true&buildA=false&format=xml"
        # Parse the contents of the HTTP request as an XML string:
        xml = None
        with urllib.request.urlopen(request_str) as r:
            if verbose:
                print(f"Requesting ECM collation data for {index}...")
            t0 = time.time()
            contents = r.read()
            t1 = time.time()
            if verbose:
                print(f"Done in {(t1 - t0):0.2f}s.")
            if verbose:
                print("Parsing ECM collation data from request contents...")
            t0 = time.time()
            vmr_xml = et.fromstring(contents)
            t1 = time.time()
            if verbose:
                print(f"Done in {(t1 - t0):0.2f}s.")
    except Exception as err:
        print(f"Error requesting ECM collation data for index {index}: {err}")

    coll = Collation(book, singular_to_subreading, verbose)
    coll.parse_xml(vmr_xml)
    tei_xml = coll.to_xml()
    tei_xml.write(output, doctype='<!DOCTYPE TEI>', encoding='utf-8', xml_declaration=True, pretty_print=True)