from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import argparse
import traceback
from typing import TypedDict
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from multiprocessing import cpu_count
from pathlib import Path
from timeit import default_timer
from typing import Optional


class Config(TypedDict):
    ffmpeg: str
    globals: str

    # Estimated anime mean_volume: -23.5
    # Estimated anime max_volume:   -7.7
    # See: https://discord.com/channels/617136488840429598/1074057444365443205/1114388630673301515
    # Values chosen were based on a mix of personal preference and Google documentation
    # See: https://developers.google.com/assistant/tools/audio-loudness
    af_norm: str

    # Cleans up audio to improve effectiveness of silencedetect
    # See: https://superuser.com/a/1727768
    af_pass: str

    # "ametadata=print:file=-" outputs to stdout
    # d = duration of silence before it is considered as "silence"
    af_silence_detect: str

    # Pads audio to compensate for potential inaccuracies
    # Too small and some voices get cut, too big and not much silence is cut
    silence_compensate: float


def get_config() -> Config:
    DEFAULT_CONFIG = Path(__file__).parent.joinpath("default_config.json")
    USER_CONFIG = Path(__file__).parent.joinpath("config.json")

    with open(DEFAULT_CONFIG) as f:
        config = json.load(f)

    # override default config with user config
    if USER_CONFIG.is_file():
        print("-config.json keys will override their counterparts in default_config.json")
        with open(USER_CONFIG) as f:
            user_config = json.load(f)

        for k,v in user_config.items():
            config[k] = v

    return config


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("codec", choices=["opus", "mp3", "aac"], )
    parser.add_argument("input_dir", type=str)
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--quality", type=str, default=None)
    parser.add_argument("--no-normalize", default=False, action='store_true')
    parser.add_argument("--no-silence-remove", default=False, action='store_true')

    return parser.parse_args()


def os_cmd(cmd):
    #print(cmd)
    # shlex.split used for POSIX compatibility
    return cmd if sys.platform == "win32" else shlex.split(cmd)


def spaghetti(output, index, str_find, silence_compensate) -> Optional[float]:
    """
    spaghetti

    Attemps to parse the output of ffmpeg to get the fp value after str_find.
    TODO: use regex instead?
    """
    offset_start = len(str_find) + 1 # str_find=
    if output[index+offset_start:index+offset_start+2] == "0\n":
        return None
    # If there is a \n but it's not followed by a zero, change offset_end to be smaller accordingly.
    elif "\n" in output[index+offset_start:index+offset_start+4]:
        offset_end = offset_start + len(output[index+offset_start:index+offset_start+4].split("\n")[0])
    else:
        offset_end = offset_start + 4

    sil_end = None
    try:
        # Gets the value after silence_end= in stdout
        # Example output in stdout: lavfi.silence_end=0.541813
        sil_end = float(output[index+offset_start:index+offset_end]) - silence_compensate
    except ValueError as err:  # wtf
        print(f"--------\n\n<><>[Kuru Kuru Kuru Kuru]<><>\n{err}")
        print(f"Attempted to find {str_find}\n-OUTPUT-{output}")
        print(f"\n-silence_index+offset-\n{output[index+offset_start:]}\n--------")

    return sil_end


def ffmpeg_crop(file, config: Config):
    """
    returns -ss STARTING_SILENCE_END -to ENDING_SILENCE_START
    or -ss STARTING_SILENCE_END (if ENDING_SILENCE_START doesn't exist)
    """
    arg_input = f"-i \"{file}\""
    arg_output = "-f null -"
    arg_filters = f'-af "{config["af_pass"]},{config["af_silence_detect"]}"'
    cmd = f'{config["ffmpeg"]} {arg_input} {arg_filters} {arg_output}'

    output: str = subprocess.run(
        os_cmd(cmd), text=True, capture_output=True, encoding="utf8"
    ).stdout

    # spaghetti below
    SIL_END_FIND = "silence_end"
    SIL_START_FIND = "silence_start"

    # WARNING: .index() can raise ValueError's, so we must wrap them...
    sil_end = 0
    try:
        sil_index = output.index(SIL_END_FIND)
        sil_end = spaghetti(output, sil_index, SIL_END_FIND, config["silence_compensate"])
    except ValueError:
        pass
    sil_end_val = 0 if sil_end is None else max(0, sil_end)  # Clamp value
    sil_end_str = f"-ss {sil_end_val}"

    # more spaghetti below
    # we look for the last instance of silence_start
    sil_start_str = ""
    try:
        # if the output ends with silence_start, then it ends in silence
        # however, the output can end with a silence_start -> silence_end pair,
        # meaning the file does NOT end in silence!
        sil_index_end1 = output.rfind("silence_start")
        sil_index_end2 = output.rfind("silence_end")

        sil_end_1 = spaghetti(output, sil_index_end1, SIL_START_FIND, 0)
        sil_end_2 = spaghetti(output, sil_index_end2, SIL_END_FIND, 0)

        if sil_end_1 is not None and sil_end_2 is not None and sil_end_1 > sil_end_2:
            sil_start = spaghetti(output, sil_index_end1, SIL_START_FIND, -config["silence_compensate"])
            sil_start_str = "" if sil_start is None else f"-to {sil_start}"
    except ValueError:
        pass

    return sil_end_str + " " + sil_start_str

def get_file_volume(file, srcpath, config: Config, seek):
    """
    analyze the volume of a file via loudnorm
    for perl example see https://github.com/FFmpeg/FFmpeg/blob/master/tools/loudnorm.rb
    """
    arg_input = f"-i \"{file}\""
    arg_output = '-f null -'
    arg_filters = f'-af "{config["af_norm"]}:print_format=json"'
    cmd = f'{config["ffmpeg"]} -hide_banner {seek} {arg_input} {arg_filters} {arg_output}'

    output: str = subprocess.run(
        os_cmd(cmd), text=True, capture_output=True, encoding="utf8"
    ).stderr

    # remove the crap from the beginning of the output
    output_json = "{" + output[output.find('"input_i"'):]
    ln_stats = json.loads(output_json)

    # fix invalid values
    # copied from
    # https://github.com/slhck/ffmpeg-normalize/blob/78a1363e96d6e592f6b85b89de46648335e0df34/ffmpeg_normalize/_streams.py#LL372C35-L372C41

    for key in [
        "input_i",
        "input_tp",
        "input_lra",
        "input_thresh",
        "output_i",
        "output_tp",
        "output_lra",
        "output_thresh",
        "target_offset",
    ]:
        # handle infinite values
        if float(ln_stats[key]) == -float("inf"):
            ln_stats[key] = -99
        elif float(ln_stats[key]) == float("inf"):
            ln_stats[key] = 0
        else:
            # convert to floats
            ln_stats[key] = float(ln_stats[key])

    return f':measured_I={ln_stats["input_i"]}:measured_LRA={ln_stats["input_lra"]}:measured_tp={ln_stats["input_tp"]}:measured_thresh={ln_stats["input_thresh"]}:offset={ln_stats["target_offset"]}'



def ffmpeg_run(file, codec, destination, quality, srcpath, config: Config, no_normalize, no_silence_remove):
    try:
        arg_input = f"-i \"{file}\""
        # codec = "flac"
        arg_output = f"\"{destination.joinpath(file.relative_to(srcpath)).with_suffix(codec)}\""
        #arg_filters = "" if no_normalize else f'-af "{config["af_norm"]}"'
        #print(f"The input arg is {arg_input} and the output args to to ffmpeg is {arg_output}")
        seek = "" if no_silence_remove else ffmpeg_crop(file, config)
        arg_filters = ""
        arg_filters_ls = []
        if not no_normalize:
            measured = get_file_volume(file, srcpath, config, seek)
            # arg_filters = f'-af "{config["af_norm"]}{measured}"'
            arg_filters_ls.append(f'{config["af_norm"]}{measured}')

        # arg_filters_ls.append('volume=1.8')
        arg_filters = "-af " + '"' + ",".join(arg_filters_ls) + '"'
        cmd = f'{config["ffmpeg"]} {config["globals"]} {seek} {arg_input} {arg_filters} {quality} {arg_output}'

        subprocess.run(os_cmd(cmd))
    except Exception as e:
        # effectively skip error if exists
        print("ERROR ON FILE:", file)
        traceback.print_exception(e)


def is_supported_audio_file(path):
    """
    copy-paste from local-audio-yomichan and jpod_index.py
    """
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        return False
    # audio container formats supposedly supported by browsers (excluding webm since it's typically for videos)
    if path.suffix.lower() not in ['.mp3', '.m4a', '.aac', '.ogg', '.oga', '.opus', '.flac', '.wav']:
        print(f"(ffmpegmulti) skipping non-audio file: {path}")
        return False

    return True


def main():
    config = get_config()
    args = get_args()

    if args.codec == "opus":
        codec = ".opus"
        quality = "-map_metadata -1 -application voip -b:a 32k"
    elif args.codec == "mp3":
        codec = ".mp3"
        quality = "-map_metadata -1 -q:a 3"
    elif args.codec == "aac":
        codec = ".aac"
        quality = "" # The user should probably specify this
    else:
        raise RuntimeError("this should not be reached")
    
    codec = ".flac"
    quality = "-map_metadata -1 -sample_fmt s16"

    # overrides default quality with user specified quality, if exists
    if args.quality is not None:
        quality = args.quality

    forvo = Path(args.input_dir)
    destination = Path(args.output_dir)
    if not forvo.is_dir():
        raise RuntimeError(f"input dir is not valid: {forvo}")

    # copy directory tree from source if the dest dir doesn't exist
    if not destination.is_dir():
        print("-Making destination directories...")
        for dirpath, dirnames, _ in os.walk(forvo):
            for dirname in dirnames:
                src_dir = os.path.join(dirpath, dirname)
                dest_dir = os.path.join(destination, os.path.relpath(src_dir, forvo))
                os.makedirs(dest_dir, exist_ok=True)

    print("-Running; let it cook...")

    start = default_timer()

    files = [file for file in filter(is_supported_audio_file, forvo.rglob("*"))]
    files_total = len(files)

    with ProcessPoolExecutor(max_workers=(cpu_count()-1)) as ex:
        files_count = 0
        for _ in ex.map(ffmpeg_run, files, repeat(codec), repeat(destination), repeat(quality), repeat(forvo), repeat(config), repeat(args.no_normalize), repeat(args.no_silence_remove)):
            files_count += 1
            print(f"-PROGRESS: {files_count}/{files_total}", end="\r", flush=True)

    elapsed = default_timer() - start

    print(f"\n-Number of files processed: {files_count}")
    print(f"-ELAPSED TIME: {elapsed/60:.3}m {elapsed%60:.3}s")


if __name__ == "__main__":
    main()
