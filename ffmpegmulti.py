import shlex
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from timeit import default_timer

FFMPEG = "ffmpeg.exe"
GLOBALS = "-loglevel warning -y"

AF_NORM = "speechnorm=p=0.5:e=6.25:r=0.0001:l=1"
#AF_PASS = "lowpass=f=3000,highpass=f=200,arnndn=m=cb.rnnn"
#AF_PASS = "lowpass=f=1000,highpass=f=200,afftdn=nf=-25"
#AF_PASS = "lowpass=f=1000,highpass=f=200,afftdn" # CANDIDATE
#AF_PASS = "lowpass=f=1000,highpass=f=200,arnndn=m=sh.rnnn"
#AF_PASS = "lowpass=f=1000,highpass=f=200,afftdn=nf=-25=tn=1"
AF_PASS = "highpass=f=300,asendcmd=0.0 afftdn sn start,asendcmd=1.5 afftdn sn stop,afftdn=nf=-20,dialoguenhance,lowpass=f=3000"



# "ametadata=print:file=-" outputs to stdout
# d = duration of silence before it is considered as "silence"
AF_SILENCE_DETECT = "silencedetect=n=-50dB:d=0.01,ametadata=print:file=-"

# Subtracts from silence_end to compensate for potential inaccuracies
# Too small and some voices get cut, too big and not much silence is cut
SILENCE_COMPENSATE = 0.2

QUALITY = "-q:a 4"
DESTINATION = "forvo_files_new/"
CODEC = ".mp3"


def os_cmd(cmd):
    # shlex.split used for POSIX compatibility
    return cmd if sys.platform == "win32" else shlex.split(cmd)


def ffmpeg_silence_end(file):
    arg_input = f"-i {file}"
    arg_output = "-f null -"
    arg_filters = f'-af "{AF_PASS},{AF_SILENCE_DETECT}"'
    cmd = f"{FFMPEG} {arg_input} {arg_filters} {arg_output}"

    output = subprocess.run(
        os_cmd(cmd), text=True, capture_output=True, encoding="utf8"
    ).stdout

    # Spaghetti below
    sil_end = 0
    try:
        sil_index = output.index("silence_end")
    except ValueError:  # Silence not found
        pass
    else:
        try:
            # Gets the value after silence_end= in stdout
            # Example output in stdout: lavfi.silence_end=0.541813
            sil_end = float(output[sil_index+12:sil_index+16]) - SILENCE_COMPENSATE
        except ValueError as err:  # wtf
            print(f"Kuru Kuru Kuru Kuru\n{err}")
            print(f"{output}\n\nsilence_index+12={output[sil_index+12:]}\n")

    return max(0, sil_end)  # Clamp value


def ffmpeg_run(file):
    arg_input = f"-i {file}"
    arg_output = f"{DESTINATION}{file.parent.stem}/{file.stem}{CODEC}"
    arg_filters = f'-af "{AF_NORM}"'
    seek = f"-ss {ffmpeg_silence_end(file)}"
    cmd = f"{FFMPEG} {GLOBALS} {seek} {arg_input} {arg_filters} {QUALITY} {arg_output}"

    subprocess.run(os_cmd(cmd))


def main():
    if (args_num := len(sys.argv)) != 3:
        raise SystemExit(f"Found {args_num} arguments but expected exactly 3")
    if (cpu_cores := int(sys.argv[1])) > 64 or (cpu_cores <= 0):
        raise ValueError("Sus core count")
    if (forvo := Path(sys.argv[2])).name != "forvo_files":
        raise SystemExit('"forvo_files" folder not found')

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
