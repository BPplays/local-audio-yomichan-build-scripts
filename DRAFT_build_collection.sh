#!/bin/bash

## THIS HAS NOT BEEN TESTED YET. It's my attempt to collect all the commands that I have run in the building of the collection so far.
#
# To start, place all <source>_files inside the input/ directory. It should look like:
# input/
#   forvo_files
#   jpod_alternate_files
#   jpod_files
#   nhk16_files
#   shinmeikai8_files
#
#   Make sure you set your ffmpeg path in the ffmpegmulti config, if needed

# https://gist.github.com/vncsna/64825d5609c146e80de8b1fd623011ca
set -euxo pipefail
SCRIPT_PATH=$(dirname -- "${BASH_SOURCE[0]}")


# stolen from yomichan_import
# downloads JMdict raw file
function refresh_source () {
    NOW=$(date '+%s')
    YESTERDAY=$((NOW - 86400)) # 86,400 seconds in 24 hours
    if [ ! -f "temp/$1" ]; then
        wget "ftp.edrdg.org/pub/Nihongo/$1.gz" -O "temp/$1.gz"
        gunzip -c "temp/$1.gz" > "temp/$1"
    elif [[ $YESTERDAY -gt $(date -r "temp/$1" '+%s') ]]; then
        rsync "ftp.edrdg.org::nihongo/$1" "temp/$1"
    fi
}

mkdir -p output/{opus,mp3}/user_files
# run ffmpegmulti script to normalize audio, trim silence from beginning and end, and convert to both opus and mp3.
python "$SCRIPT_PATH/ffmpegmulti.py" opus input/forvo_files output/opus/user_files/forvo_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/forvo_files output/mp3/user_files/forvo_files

# remove broken file
rm output/opus/user_files/forvo_files/skent/解く.opus
rm output/mp3/user_files/forvo_files/skent/解く.mp3

python "$SCRIPT_PATH/ffmpegmulti.py" opus input/shinmeikai8_files output/opus/user_files/shinmeikai8_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/shinmeikai8_files output/mp3/user_files/shinmeikai8_files

sed 's/.aac/.opus/g' input/shinmeikai8_files/index.json > output/opus/user_files/shinmeikai8_files/index.json
sed 's/.aac/.mp3/g' input/shinmeikai8_files/index.json > output/mp3/user_files/shinmeikai8_files/index.json

python "$SCRIPT_PATH/ffmpegmulti.py" opus input/nhk16_files output/opus/user_files/nhk16_files
python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/nhk16_files output/mp3/user_files/nhk16_files

sed 's/.aac/.opus/g' input/nhk16_files/entries.json > output/opus/user_files/nhk16_files/entries.json
sed 's/.aac/.mp3/g' input/nhk16_files/entries.json > output/mp3/user_files/nhk16_files/entries.json

# Build an index of the jpod files and remove duplicates
python "$SCRIPT_PATH/jpod_index.py"

# Convert jpod files
python "$SCRIPT_PATH/ffmpegmulti.py" --no-silence-remove opus temp/jpod output/opus/user_files/jpod_files
python "$SCRIPT_PATH/ffmpegmulti.py" --no-silence-remove mp3 temp/jpod output/mp3/user_files/jpod_files

sed 's/.mp3/.opus/g' temp/jpod/index.json > output/opus/user_files/jpod_files/index.json
cp temp/jpod/index.json output/mp3/user_files/jpod_files/index.json

# Generates jmdict_forms.json
refresh_source "JMdict_e"
python "$SCRIPT_PATH/parse_jmdict.py"



# TODO create a zip of the outputted folder
# NOTE: do NOT include `output/jpod/temp_index.json` in the zip
