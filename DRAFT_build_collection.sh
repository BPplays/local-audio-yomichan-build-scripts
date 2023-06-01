#!/bin/bash

## THIS HAS NOT BEEN TESTED YET. It's my attempt to collect all the commands that I have run in the building of the collection so far.

# https://gist.github.com/vncsna/64825d5609c146e80de8b1fd623011ca
set -euxo pipefail
SCRIPT_PATH=$(dirname -- "${BASH_SOURCE[0]}")
FFMPEG_PATH="ffmpeg"

mkdir -p {opus,mp3}_out/user_files
# run ffmpegmulti script to normalize audio, trim silence from beginning and end, and convert to both opus and mp3.
python "$SCRIPT_PATH/ffmpegmulti.py" opus forvo_files opus_out/user_files/forvo_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 forvo_files mp3_out/user_files/forvo_files

python "$SCRIPT_PATH/ffmpegmulti.py" opus shinmeikai8_files opus_out/user_files/shinmeikai8_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 shinmeikai8_files mp3_out/user_files/shinmeikai8_files

sed 's/.aac/.opus/g' shinmeikai8_files/index.json > opus_out/user_files/shinmeikai8_files/index.json
sed 's/.aac/.mp3/g' shinmeikai8_files/index.json > mp3_out/user_files/shinmeikai8_files/index.json

# convert nhk16 files without any extra processing
mkdir -p {opus,mp3}_out/nhk16_files/audio
find nhk16_files/ -type f -name "*.aac" -print0 | parallel -0 --progress "$FFMPEG_PATH" -loglevel warning -i "{}" -b:a 32k "nhk16_files_opus/audio/{/.}.opus"
find nhk16_files/ -type f -name "*.aac" -print0 | parallel -0 --progress "$FFMPEG_PATH" -loglevel warning -i "{}" -q:a 3 "nhk16_files_mp3/audio/{/.}.mp3"

sed 's/.aac/.opus/g' nhk16_files/entries.json > opus_out/user_files/nhk16_files/entries.json
sed 's/.aac/.mp3/g' nhk16_files/entries.json > mp3_out/user_files/nhk16_files/entries.json

# remove exact duplicates across jpod and jpod alt
python "$SCRIPT_PATH/compare.py" delete


### TODO stuff for jpod

### TODO remove known broken files


