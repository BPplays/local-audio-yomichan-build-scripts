from __future__ import annotations

"""
Converts our jpod audio (from jpod_files and jpod_alternate_files) into a
unified `jpod` source, compatible with AJT Japanese.
"""

import os
import json
import shutil
import hashlib
import argparse
from dataclasses import dataclass
from typing import TypedDict, NewType, NotRequired, Any

# TypedDict classes and FileList copied/pasted from AJT Japanese

TEMP_INDEX = "output/jpod/temp_index.json"
OUT_INDEX = "output/jpod/index.json"

FileList = list[str]

class FileInfo(TypedDict):
    kana_reading: NotRequired[str]
    pitch_pattern: NotRequired[str]
    pitch_number: str


class SourceMeta(TypedDict):
    name: str
    year: int
    version: int
    media_dir: str
    media_dir_abs: NotRequired[str]


class SourceIndex(TypedDict):
    meta: SourceMeta
    headwords: dict[str, FileList]
    files: dict[str, FileInfo]


CheckSum = str
class TermInfo(TypedDict):
    term: str
    reading: str | None
    file: str


JpodIndex = dict[CheckSum, list[TermInfo]]


def is_kana(word):
    for char in word:
        if char < "ぁ" or char > "ヾ":
            return False
    return True


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-jpod-index-gen", action="store_true")
    parser.add_argument("--no-index-gen", action="store_true")
    return parser.parse_args()


def parse_directory(input_dir: str, index: JpodIndex):

    # copy/paste from local audio add-on
    for root, _, files in os.walk(input_dir, topdown=False):
        for name in files:
            path = os.path.join(root, name)

            relative_path = os.path.relpath(path, input_dir)

            if not name.endswith(".mp3"):
                print(
                    f"(jpod_index) skipping non-mp3 file: {relative_path}"
                )
                continue

            parts = name.removesuffix(".mp3").split(" - ")
            if len(parts) != 2:
                print(
                    f"(jpod_index) skipping file with ' - ' sep: {relative_path}"
                )
                continue
            reading, term = parts

            # usually, jpod file names are formatted as:
            # "reading - term.mp3"
            # however, sometimes, the reading section is just the term (even if the term is kanji)
            if reading == term and not is_kana(reading):
                reading = None

            # checksums: https://stackoverflow.com/a/16876405
            with open(path, 'rb') as f:
                data = f.read()
                md5 = hashlib.md5(data).hexdigest()

                # ASSUMPTION: a unique md5 == unique file contents
                # (should be safe to assume since we're not dealing with petabytes of data,
                # and we're not dealing with potentially adverse data)
                if md5 not in index:
                    index[md5] = []

                index[md5].append({"term": term, "reading": reading, "file": path})

def add_terms_to_ajt_index(terms: list[TermInfo], ajt_index: SourceIndex, md5: str, reading_override: str | None = None):
    assert len(terms) > 0
    MEDIA_DIR = "output/jpod/media"

    reading = reading_override
    og_file_name = terms[0]["file"]
    new_file_name = md5 + ".mp3" # NOTE: hard coded mp3 because original files should all be mp3
    shutil.copy(og_file_name, os.path.join(MEDIA_DIR, new_file_name))

    for term_info in terms:
        # gets the first reading from the terms
        # ASSUMPTION: readings are unique (see parse_index for this parsing)
        if reading is None:
            reading = term_info.get("reading", None)

        term = term_info["term"]
        if term not in ajt_index["headwords"]:
            ajt_index["headwords"][term] = []
        if new_file_name not in ajt_index["headwords"][term]:
            ajt_index["headwords"][term].append(new_file_name)

    file_info: Any = {} # Any because I'm too lazy to get typing to work here
    if reading is not None:
        file_info["kana_reading"] = reading
    file_info["pitch_number"] = "?" # all pitches are unknown

    assert new_file_name not in ajt_index["files"]
    ajt_index["files"][new_file_name] = file_info



def parse_index(index: JpodIndex):
    # counts the number of files that have duplicate readings
    # (does NOT count number of words that are skipped!)
    counter = 0

    jpod_audio_unique = 0
    ajt_index: SourceIndex = {
        "meta": {
            "name": "JapanesePod101",
            "year": 2020, # NOTE: don't know when the audio was scraped
            "version": 1,
            "media_dir": "media",
        },
        "headwords": {},
        "files": {},
    }

    for md5 in index:
        ajt_reading = None

        jpod_counter = 0
        readings = set()
        terms = index[md5]
        for term_info in terms:
            reading = term_info["reading"]
            if reading is not None and reading not in readings:
                readings.add(reading)

            file = term_info["file"]
            if "jpod_files" in file:
                jpod_counter += 1
                ajt_reading = term_info["reading"]

        if len(readings) > 2:
            #print(index[md5])
            counter += 1
            if jpod_counter > 1:
                jpod_audio_unique += 1
                # we do NOT add the audio here, because there are multiple readings,
                # and there is no jpod source to refer to as the 'golden standard' reading
            elif jpod_counter == 1:
                # ASSUMPTION: jpod source has the correct reading
                assert ajt_reading is not None
                add_terms_to_ajt_index(terms, ajt_index, md5, ajt_reading)

        else:
            # unique reading for the word, safe to use!
            add_terms_to_ajt_index(terms, ajt_index, md5)

    assert jpod_audio_unique == 0
    print(f"Skipped duplicates: {counter}")

    with open(OUT_INDEX, "w") as f:
        json.dump(ajt_index, f, ensure_ascii=False, indent=2)

def create_jpod_index():
    index: JpodIndex = {}
    parse_directory("input/jpod_files", index)
    parse_directory("input/jpod_alternate_files", index)
    with open(TEMP_INDEX, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def main():
    # TODO: create required directories:
    # output
    # output/jpod
    # output/jpod/media

    args = get_args()

    if not args.no_jpod_index_gen:
        create_jpod_index()

    # creates ajt japanese index file
    # NOTE: a unique file must be created per reading.
    # However, our data occasionally has one file for multiple readings.
    # These will be emitted as a warning.
    if not args.no_index_gen:
        with open(TEMP_INDEX) as f:
            index = json.load(f)
        parse_index(index)

if __name__ == "__main__":
    main()
