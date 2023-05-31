from __future__ import annotations

import shlex
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from timeit import default_timer
from typing import Optional

#FFMPEG = "ffmpeg.exe"
FFMPEG = "/home/austin/i/mpv-build/mpv-build/ffmpeg_build/ffmpeg"
#FFMPEG = "ffmpeg"
GLOBALS = "-loglevel warning -y"

# we keep the normalization as 0.5 to match closer to nhk16 audio
# and to match the new flags from stegatxins0-mining
AF_NORM = "speechnorm=p=0.5:e=6.25:r=0.0001:l=1"
AF_PASS = "highpass=f=300,asendcmd=0.0 afftdn sn start,asendcmd=1.5 afftdn sn stop,afftdn=nf=-20,dialoguenhance,lowpass=f=3000"



# "ametadata=print:file=-" outputs to stdout
# d = duration of silence before it is considered as "silence"
AF_SILENCE_DETECT = "silencedetect=n=-50dB:d=0.01,ametadata=print:file=-"

# Subtracts from silence_end to compensate for potential inaccuracies
# Too small and some voices get cut, too big and not much silence is cut
SILENCE_COMPENSATE = 0.2

#QUALITY = "-q:a 4"
QUALITY = "-b:a 32k" # OPUS
DESTINATION = "forvo_files_new/"
CODEC = ".opus"


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


def ffmpeg_crop(file):
    """
    returns -ss STARTING_SILENCE_END -to ENDING_SILENCE_START
    or -ss STARTING_SILENCE_END (if ENDING_SILENCE_START doesn't exist)
    """
    arg_input = f"-i {file}"
    arg_output = "-f null -"
    arg_filters = f'-af "{AF_PASS},{AF_SILENCE_DETECT}"'
    cmd = f"{FFMPEG} {arg_input} {arg_filters} {arg_output}"

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
        sil_end = spaghetti(output, sil_index, SIL_END_FIND, SILENCE_COMPENSATE)
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
            sil_start = spaghetti(output, sil_index_end1, SIL_START_FIND, -1*SILENCE_COMPENSATE)
            sil_start_str = "" if sil_start is None else f"-to {sil_start}"
    except ValueError:
        pass

    return sil_end_str + " " + sil_start_str


def ffmpeg_run(file):
    arg_input = f"-i {file}"
    arg_output = f"{DESTINATION}{file.parent.stem}/{file.stem}{CODEC}"
    arg_filters = f'-af "{AF_NORM}"'
    seek = ffmpeg_crop(file)
    cmd = f"{FFMPEG} {GLOBALS} {seek} {arg_input} {arg_filters} {QUALITY} {arg_output}"

    subprocess.run(os_cmd(cmd))


def main():
    if (args_num := len(sys.argv)) != 3:
        raise SystemExit(f"Found {args_num} arguments but expected exactly 3")
    if (cpu_cores := int(sys.argv[1])) > 64 or (cpu_cores <= 0):
        raise ValueError("Sus core count")
    forvo = Path(sys.argv[2])
    #if (forvo := Path(sys.argv[2])).name != "forvo_files":
    #    raise SystemExit('"forvo_files" folder not found')

    print("-Running; let it cook...")

    start = default_timer()

    files = [file for file in forvo.rglob("*/*")]
    files_total = len(files)

    with ProcessPoolExecutor(max_workers=cpu_cores) as ex:
        files_count = 0
        for _ in ex.map(ffmpeg_run, files):
            print(f"-PROGRESS: {files_count}/{files_total}", end="\r", flush=True)
            files_count += 1

    elapsed = default_timer() - start

    print(f"\n-Number of files processed: {files_count}")
    print(f"-ELAPSED TIME: {elapsed/60:.3}m {elapsed%60:.3}s")


if __name__ == "__main__":
    main()
