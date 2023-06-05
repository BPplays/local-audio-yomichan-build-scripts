
import os
import re
import sys
import json
import shlex
import argparse
import subprocess
import urllib.request

from pathlib import Path

NOTE_TYPE = "JP Mining Note"
AUDIO_FIELD = "SentenceAudio"
MEDIA_DIR = "/home/austin/.local/share/Anki2/Japanese/collection.media"

BASE_QUERY = f'"note:{NOTE_TYPE}" -{AUDIO_FIELD}:'
FFMPEG_CMD = f'ffmpeg -i "%s" -af volumedetect -f null -'

rx_AUDIO_FILE = re.compile(r'\[sound:(.+)\]')
# [Parsed_volumedetect_0 @ 0x565118092980] n_samples: 280287
# [Parsed_volumedetect_0 @ 0x565118092980] mean_volume: -22.8 dB
# [Parsed_volumedetect_0 @ 0x565118092980] max_volume: -4.7 dB
# [Parsed_volumedetect_0 @ 0x565118092980] histogram_4db: 3
# [Parsed_volumedetect_0 @ 0x565118092980] histogram_5db: 9
# [Parsed_volumedetect_0 @ 0x565118092980] histogram_6db: 42
# [Parsed_volumedetect_0 @ 0x565118092980] histogram_7db: 127
# [Parsed_volumedetect_0 @ 0x565118092980] histogram_8db: 270
rx_MEAN_VOLUME = re.compile(r'mean_volume: (-?\d+(\.\d+)?) dB')
rx_MAX_VOLUME = re.compile(r'max_volume: (-?\d+(\.\d+)) dB')

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def run_cmd(cmd):
    parsed_cmd = cmd if sys.platform == "win32" else shlex.split(cmd)
    return subprocess.run(
        parsed_cmd, text=True, capture_output=True, encoding="utf8"
    )


def get_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    sentence = subparsers.add_parser('sentence')
    sentence.add_argument("tag", type=str)
    sentence.set_defaults(type="sentence")

    local_audio = subparsers.add_parser('local_audio')
    local_audio.add_argument("folder", type=str)
    local_audio.add_argument("ratio", type=float, default="1000")
    local_audio.set_defaults(type="local_audio")

    return parser.parse_args()


def get_ffmpeg_number(rx, output):
    """
    better version of spaghetti()
    """
    search_result = rx.search(output)
    float_result = None
    if search_result is not None:
        float_result = float(search_result.group(1))
    return float_result


def main():
    args = get_args()

    # NOTE: dB is a logarithmic. A simple average is likely not the correct way of measuring average dB.
    avg_max = 0
    avg_max_n = 0
    avg_mean = 0
    avg_mean_n = 0

    if args.type == "sentence":
        query = f'{BASE_QUERY} "tag:{args.tag}"'
        notes: list[int] = invoke("findNotes", query=query)
        print("Found", len(notes), "notes.")
        if len(notes) == 0:
            return
        print("Getting note info...")
        notes_info = invoke("notesInfo", notes=notes)
        for note_info in notes_info:
            sentence_audio = note_info["fields"][AUDIO_FIELD]["value"]
            search_result = rx_AUDIO_FILE.search(sentence_audio.strip())
            if search_result is None:
                continue
            audio_file = search_result.group(1)
            cmd_result = run_cmd(FFMPEG_CMD % os.path.join(MEDIA_DIR, audio_file))
            output = cmd_result.stderr # WHY does it use stderr?

            mean_result_float = get_ffmpeg_number(rx_MEAN_VOLUME, output)
            if mean_result_float is not None:
                avg_mean += mean_result_float
                avg_mean_n += 1

            max_result_float = get_ffmpeg_number(rx_MAX_VOLUME, output)
            if max_result_float is not None:
                avg_max += max_result_float
                avg_max_n += 1

            print(audio_file, mean_result_float, max_result_float)

        print("avg max:", avg_max / avg_max_n, "avg mean:", avg_mean / avg_mean_n)

    else: # local_audio
        folder = Path(args.folder)
        ratio = args.ratio
        for i, path in enumerate(folder.rglob("*")):
            if i % ratio == 0:
                cmd_result = run_cmd(FFMPEG_CMD % str(path))
                output = cmd_result.stderr # WHY does it use stderr?

                mean_result_float = get_ffmpeg_number(rx_MEAN_VOLUME, output)
                if mean_result_float is not None:
                    avg_mean += mean_result_float
                    avg_mean_n += 1

                max_result_float = get_ffmpeg_number(rx_MAX_VOLUME, output)
                if max_result_float is not None:
                    avg_max += max_result_float
                    avg_max_n += 1

                print(path, mean_result_float, max_result_float)
        print("avg max:", avg_max / avg_max_n, "avg mean:", avg_mean / avg_mean_n, "files:", avg_max_n+avg_mean_n/2)


if __name__ == "__main__":
    main()
