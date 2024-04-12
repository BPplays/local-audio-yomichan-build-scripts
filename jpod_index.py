from __future__ import annotations

"""
Converts our jpod audio (from jpod_files and jpod_alternate_files) into a
unified `jpod` source, compatible with AJT Japanese.

Additionally, this script does the following:
- Remove duplicate files (using the md5 checksum)
- Remove all files that have more than one reading associated with it
    - UNLESS there exists one and only one reading in `jpod_files`, which we use as the gold standard

Requires Python 3.11 to use NotRequired
"""

import os
import json
import shutil
import hashlib
import argparse
import time
import sys
import textwrap
import wcwidth
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, NewType, NotRequired, Any

import atexit

def disable_cursor():
    print("\033[?25l", end='', flush=True)  # Disable cursor

def enable_cursor():
    print("\033[?25h", end='', flush=True)  # Enable cursor

# Register enable_cursor to be called on exit
atexit.register(enable_cursor)

# TypedDict classes and FileList copied/pasted from AJT Japanese

TEMP_INDEX = "temp/jpod/temp_index.json"
OUT_INDEX = "temp/jpod/index.json"
OUT_MEDIA = "temp/jpod/media"


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

def is_supported_audio_file(path):
    """
    copy-paste from local-audio-yomichan
    """
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        return False
    # audio container formats supposedly supported by browsers (excluding webm since it's typically for videos)
    if not path.suffix.lower() in ['.mp3', '.m4a', '.aac', '.ogg', '.oga', '.opus', '.flac', '.wav']:
        print(f"(jpod_index) skipping non-audio file: {path}")
        return False

    return True
LINE_UP = '\033[1A'
LINE_CLEAR = '\x1b[2K'

def delete_previous_line(lu):
    # sys.stdout.write('\033[F')  # Move cursor up one line
    # sys.stdout.write('\033[K')  # Clear the line
    if lu:
        print(LINE_UP, end=LINE_CLEAR)
    else:
        print(end=LINE_CLEAR)
    
    
def add_newline_every_terminal_width(text):
    terminal_width = os.get_terminal_size().columns
    lines = text.split('\n')
    result = ''
    for line in lines:
        line_width = 0
        for char in line:
            char_width = wcwidth.wcwidth(char)
            if char_width < 0:  # Treat control characters as width 0
                char_width = 0
            line_width += char_width
            if line_width >= terminal_width:
                result += '\n'
                line_width = char_width
            result += char
        result += '\n'
    return result

def parse_directory(input_dir: str, index: JpodIndex):
    # copy/paste from local audio add-on
    path_th = 100
    loops = 0
    paths = filter(is_supported_audio_file, Path(input_dir).rglob("*"))
    print("printing every "+str(path_th)+" files")
    last_time = 0
    last_loops = 0
    pd_print = ""
    fps = 0
    last_fps = 0
    last_path = ""
    print_path = ""
    num_lines = 0

    for path in paths:
        # print(pd_print)
        
        if (not fps == last_fps) or (not print_path == last_path):
            last_path = print_path
            last_fps = fps
            # print(LINE_UP, end=LINE_CLEAR)
            for i in range(num_lines):
                if i == 0:
                    delete_previous_line(False)
                else:
                    delete_previous_line(True)

            # print("files per second", fps)
            # print("files per second", fps)
            # print("path (prints ever 20th)", print_path)
            terminal_width = shutil.get_terminal_size().columns
            pd_print = pd_print + "files per second: "+str(fps)+"\n"
            pd_print = pd_print + "total files: "+str(loops)+"\n"
            pd_print = pd_print + "path (prints every "+str(path_th)+"): "+str(print_path)
            # wrapped_textl = textwrap.wrap(pd_print, width=terminal_width-1)
            # wrapped_text = "\n".join(wrapped_textl)
            wrapped_text = add_newline_every_terminal_width(pd_print)
            disable_cursor()
            print(wrapped_text, end="")
            num_lines = len(wrapped_text.split('\n'))
            pd_print = ""
            
            
        
        # pd_print = ""
        if loops == 0:
            last_time = time.time()
            
        
        if time.time() - last_time >= 10:
            fps = (loops - last_loops) / (time.time() - last_time)
            last_loops = loops
            last_time = time.time()
            # print("files per second", loops_per_sec)
            
        
        loops = loops + 1
        relative_path = str(path.relative_to(Path(input_dir).parent))
        # Remove known broken files
        if relative_path in ("jpod_files/かえる - 蛙.mp3", "jpod_files/きゅうりょうび - 給料日.mp3",
                             "jpod_files/ひとり - 一人.mp3", "jpod_files/くばる - 配る.mp3",
                             "jpod_files/せいえん - 声援.mp3", "jpod_files/こうこく - 広告.mp3"):
            # print(f"Excluding known broken file {relative_path}")
            print_path = f"Excluding known broken file {relative_path}"
            continue
        elif loops % path_th == 0:
            # print(path)
            print_path = path

        basename_noext = path.stem
        parts = basename_noext.split(" - ")

        # Cannot parse required fields from a filename missing a " - " separator.
        if len(parts) != 2:
            # print(
            #     f"(jpod_index) skipping file without ' - ' sep: {relative_path}"
            # )
            print_path = f"(jpod_index) skipping file without ' - ' sep: {relative_path}"
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

            index[md5].append({"term": term, "reading": reading, "file": str(path)})
    print()
    
    

def add_terms_to_ajt_index(terms: list[TermInfo], ajt_index: SourceIndex, md5: str, reading_override: str | None = None):
    assert len(terms) > 0

    reading = reading_override
    og_file_name = terms[0]["file"]
    new_file_name = md5 + ".mp3" # NOTE: hard coded mp3 because original files should all be mp3
    # It's okay for wav files to have a .mp3 extension for this temporary purpose. ffmpeg will detect by file content.
    shutil.copy(og_file_name, os.path.join(OUT_MEDIA, new_file_name))

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
    # counts the number of words that are removed
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

        if len(readings) >= 2:
            #print(index[md5])
            if jpod_counter > 1:
                jpod_audio_unique += 1
                # we do NOT add the audio here, because there are multiple readings,
                # and there is no jpod source to refer to as the 'golden standard' reading
                counter += len(readings)
            elif jpod_counter == 1:
                # ASSUMPTION: jpod source has the correct reading
                assert ajt_reading is not None
                add_terms_to_ajt_index(terms, ajt_index, md5, ajt_reading)
            else:
                counter += len(readings)

        else:
            # unique reading for the word, safe to use!
            add_terms_to_ajt_index(terms, ajt_index, md5)

    print(f"Gold standard failures: {jpod_audio_unique}")
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
    # Create required directories if they don't exist
    os.makedirs(OUT_MEDIA, exist_ok=True)

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
