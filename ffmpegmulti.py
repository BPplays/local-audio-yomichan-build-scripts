import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from timeit import default_timer

#FFMPEG = "ffmpeg"
FFMPEG = "/home/austin/i/mpv-build/mpv-build/ffmpeg_build/ffmpeg"
GLOBALS = "-loglevel warning -y"
OPTIONS = '-af "highpass=f=200,lowpass=f=3000,afftdn=nf=-25,silenceremove=start_periods=1:start_duration=0:start_threshold=-60dB:detection=peak,aformat=dblp,areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-60dB:detection=peak,aformat=dblp,areverse,speechnorm=p=0.5:e=6.25:r=0.0001:l=1" -q:a 4'
DESTINATION = "forvo_files_new/"
#CODEC = ".mp3"
CODEC = ".wav"


def ffmpeg_run(commands):
    subprocess.run(commands.split())


def ffmpeg_cmd_create(file):
    arg_input = f"-i {file}"
    arg_output = f"{DESTINATION}{file.parent.stem}/{file.stem}{CODEC}"
    return f"{FFMPEG} {GLOBALS} {arg_input} {OPTIONS} {arg_output}"


def main():
    if (args_num := len(sys.argv)) != 3:
        raise SystemExit(f"Found {args_num} arguments but expected exactly 3")
    if (cpu_cores := int(sys.argv[1])) > 64 or (cpu_cores <= 0):
        raise ValueError("Sus core count")
    if (forvo := Path(sys.argv[2])).name != "forvo_files":
        raise SystemExit("\"forvo_files\" folder not found")

    print("-Running; let it cook...")

    start = default_timer()

    ffmpeg_cmds = [ffmpeg_cmd_create(file) for file in forvo.rglob("*/*")]
    ffmpeg_cmds_total = len(ffmpeg_cmds)
    
    with ProcessPoolExecutor(max_workers=cpu_cores) as ex:
        files_num = 0
        for _ in ex.map(ffmpeg_run, ffmpeg_cmds):
            print(f"-PROGRESS: {files_num}/{ffmpeg_cmds_total}", end="\r", flush=True)
            files_num += 1

    elapsed = default_timer() - start

    print(f"\n-Number of files processed: {files_num}")
    print(f"-ELAPSED TIME: {elapsed/60:.3}m {elapsed%60:.3}s")


if __name__ == "__main__":
    main()
