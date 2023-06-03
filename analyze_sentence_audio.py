
import re
import sys
import json
import shlex
import argparse
import subprocess
import urllib.request

NOTE_TYPE = "JP Mining Note"
AUDIO_FIELD = "SentenceAudio"
MEDIA_DIR = "/home/austin/.local/share/Anki2/Japanese/collection.media"

BASE_QUERY = f'"note:{NOTE_TYPE}" -{AUDIO_FIELD}:'
FFMPEG_CMD = f'ffmpeg -i {MEDIA_DIR}/%s -af volumedetect -f null -'

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
    parser.add_argument("tag", type=str)
    return parser.parse_args()


def main():
    args = get_args()
    query = f'{BASE_QUERY} "tag:{args.tag}"'

    # NOTE: dB is a logarithmic. A simple average is likely not the correct way of measuring average dB.
    avg_max = 0
    avg_max_n = 0
    avg_mean = 0
    avg_mean_n = 0

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
        cmd_result = run_cmd(FFMPEG_CMD % audio_file)
        output = cmd_result.stderr # WHY does it use stderr?

        mean_result = rx_MEAN_VOLUME.search(output)
        mean_result_float = None
        if mean_result is not None:
            mean_result_float = float(mean_result.group(1))
            avg_mean += mean_result_float
            avg_mean_n += 1

        max_result = rx_MAX_VOLUME.search(output)
        max_result_float = None
        if max_result is not None:
            max_result_float = float(max_result.group(1))
            avg_max += max_result_float
            avg_max_n += 1

        print(audio_file, mean_result_float, max_result_float)

    print("avg max:", avg_max / avg_max_n, "avg mean:", avg_mean / avg_mean_n)


if __name__ == "__main__":
    main()
