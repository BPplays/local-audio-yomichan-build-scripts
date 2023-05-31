from __future__ import annotations

import json
import shlex
import subprocess
import sys
import argparse
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

    # we keep the normalization as 0.5 to match closer to nhk16 audio
    # and to match the new flags from stegatxins0-mining
    af_norm: str
    af_pass: str

    # "ametadata=print:file=-" outputs to stdout
    # d = duration of silence before it is considered as "silence"
    af_silence_detect: str

    # Pads audio compensate for potential inaccuracies
    # Too small and some voices get cut, too big and not much silence is cut
    silence_compensate: float


def get_config() -> Config:
    DEFAULT_CONFIG = Path(__file__).parent.joinpath("default_config.json")
    USER_CONFIG = Path(__file__).parent.joinpath("config.json")

    with open(DEFAULT_CONFIG) as f:
        config = json.load(f)

    # override default config with user config
    if USER_CONFIG.is_file():
        with open(USER_CONFIG) as f:
            user_config = json.load(f)

        for k,v in user_config.items():
            config[k] = v

    return config


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("codec", choices=["opus", "mp3"], )
    parser.add_argument("input_dir", type=str)
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--quality", type=str, default=None)
    parser.add_argument("--no-normalize", type=bool, default=False) # TODO: use this option!
    parser.add_argument("--no-silence-remove", type=bool, default=False) # TODO: use this option!

    return parser.parse_args()


def os_cmd(cmd):
    #print(cmd)
    # shlex.split used for POSIX compatibility
    return cmd if sys.platform == "win32" else shlex.split(cmd)


def spaghetti(output, index, str_find, silence_compensate) -> Optional[float]:
    """
    spaghetti
    """
    offset_start = len(str_find) + 1 # str_find=
    if output[index+offset_start:index+offset_start+2] == "0\n":
        return None
    offset_end = offset_start + 4

    sil_end = None
    try:
        # Gets the value after silence_end= in stdout
        # Example output in stdout: lavfi.silence_end=0.541813
        sil_end = float(output[index+offset_start:index+offset_end]) - silence_compensate
    except ValueError as err:  # wtf
        print(f"Kuru Kuru Kuru Kuru\n{err}")
        print(f"{output}\n\nsilence_index+12={output[index+12:]}\n")

    return sil_end


def ffmpeg_crop(file, config: Config):
    """
    returns -ss STARTING_SILENCE_END -to ENDING_SILENCE_START
    or -ss STARTING_SILENCE_END (if ENDING_SILENCE_START doesn't exist)
    """
    arg_input = f"-i {file}"
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


def ffmpeg_run(file, codec, destination, quality, srcpath, config: Config):
    arg_input = f"-i \"{file}\""
    arg_output = f"\"{destination.joinpath(file.relative_to(srcpath)).with_suffix(codec)}\""
    arg_filters = f'-af "{config["af_norm"]}"'
    #print(f"The input arg is {arg_input} and the output args to to ffmpeg is {arg_output}")
    seek = ffmpeg_crop(file, config)
    cmd = f'{config["ffmpeg"]} {config["globals"]} {seek} {arg_input} {arg_filters} {quality} {arg_output}'

    subprocess.run(os_cmd(cmd))


def main():
    config = get_config()
    args = get_args()

    if args.codec == "opus":
        codec = ".opus"
        quality = "-b:a 32k"
    elif args.codec == "mp3":
        codec = ".mp3"
        quality = "-q:a 3"
    else:
        raise RuntimeError("this should not be reached")

    # overrides default quality with user specified quality, if exists
    if args.quality is not None:
        quality = args.quality

    forvo = Path(args.input_dir)
    destination = Path(args.output_dir)
    if not forvo.is_dir():
        raise RuntimeError(f"input dir is not valid: {forvo}")
    if not destination.is_dir():
        raise RuntimeError(f"output dir is not valid: {destination}")

    print("-Running; let it cook...")

    start = default_timer()

    files = [file for file in filter((lambda file: file.is_file()), forvo.rglob("*"))]
    files_total = len(files)

    with ProcessPoolExecutor(max_workers=(cpu_count() -1)) as ex:
        files_count = 0
        for _ in ex.map(ffmpeg_run, files, repeat(codec), repeat(destination), repeat(quality), repeat(forvo), repeat(config)):
            print(f"-PROGRESS: {files_count}/{files_total}", end="\r", flush=True)
            files_count += 1

    elapsed = default_timer() - start

    print(f"\n-Number of files processed: {files_count}")
    print(f"-ELAPSED TIME: {elapsed/60:.3}m {elapsed%60:.3}s")


if __name__ == "__main__":
    main()
