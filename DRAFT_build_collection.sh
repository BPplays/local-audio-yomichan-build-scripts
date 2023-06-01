#!/bin/bash

## THIS HAS NOT BEEN TESTED YET. It's my attempt to collect all the commands that I have run in the building of the collection so far.

# https://gist.github.com/vncsna/64825d5609c146e80de8b1fd623011ca
set -euxo pipefail
SCRIPT_PATH=$(dirname -- "${BASH_SOURCE[0]}")
FFMPEG_PATH="ffmpeg"

mkdir -p output/{opus,mp3}/user_files
# run ffmpegmulti script to normalize audio, trim silence from beginning and end, and convert to both opus and mp3.
python "$SCRIPT_PATH/ffmpegmulti.py" opus input/forvo_files output/opus/user_files/forvo_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/forvo_files output/mp3/user_files/forvo_files

python "$SCRIPT_PATH/ffmpegmulti.py" opus input/shinmeikai8_files output/opus/user_files/shinmeikai8_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/shinmeikai8_files output/mp3/user_files/shinmeikai8_files

sed 's/.aac/.opus/g' input/shinmeikai8_files/index.json > output/opus/user_files/shinmeikai8_files/index.json
sed 's/.aac/.mp3/g' input/shinmeikai8_files/index.json > output/mp3/user_files/shinmeikai8_files/index.json

# convert nhk16 files without any extra processing
python "$SCRIPT_PATH/ffmpegmulti.py" --no-silence-remove --no-normalize opus input/nhk16_files output/opus/user_files/nhk16_files
python "$SCRIPT_PATH/ffmpegmulti.py" --no-silence-remove --no-normalize mp3 input/nhk16_files output/mp3/user_files/nhk16_files

sed 's/.aac/.opus/g' input/nhk16_files/entries.json > output/opus/user_files/nhk16_files/entries.json
sed 's/.aac/.mp3/g' input/nhk16_files/entries.json > output/mp3/user_files/nhk16_files/entries.json

# remove exact duplicates across jpod and jpod alt
#python "$SCRIPT_PATH/compare.py" delete


mkdir -p output/jpod/media
python "$SCRIPT_PATH/jpod_index.py"
# TODO: convert jpod to opus


### TODO remove known broken files


# TODO create a zip of the outputted folder
# NOTE: do NOT include `output/jpod/temp_index.json` in the zip
