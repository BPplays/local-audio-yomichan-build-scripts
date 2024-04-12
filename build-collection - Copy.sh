#!/bin/bash

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
python "$SCRIPT_PATH/ffmpegmulti.py" opus input/forvo_files output/opus/user_files/forvo_files --quality "-b:a 256k"
# python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/forvo_files output/mp3/user_files/forvo_files

# remove broken file
rm output/opus/user_files/forvo_files/skent/解く.opus
# rm output/mp3/user_files/forvo_files/skent/解く.mp3

mkdir -p output/opus/user_files/shinmeikai8_files/media
# # mkdir -p output/mp3/user_files/shinmeikai8_files/media
python "$SCRIPT_PATH/ffmpegmulti.py" opus input/shinmeikai8_files/media output/opus/user_files/shinmeikai8_files/media --quality "-b:a 256k"
# # python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/shinmeikai8_files/media output/mp3/user_files/shinmeikai8_files/media

sed 's/.aac/.opus/g' input/shinmeikai8_files/index.json > output/opus/user_files/shinmeikai8_files/index.json
# sed 's/.aac/.mp3/g' input/shinmeikai8_files/index.json > output/mp3/user_files/shinmeikai8_files/index.json

mkdir -p output/opus/user_files/nhk16_files/audio
# mkdir -p output/mp3/user_files/nhk16_files/audio
python "$SCRIPT_PATH/ffmpegmulti.py" opus input/nhk16_files/audio output/opus/user_files/nhk16_files/audio --quality "-b:a 256k"
# python "$SCRIPT_PATH/ffmpegmulti.py" mp3 input/nhk16_files/audio output/mp3/user_files/nhk16_files/audio

sed 's/.aac/.opus/g' input/nhk16_files/entries.json > output/opus/user_files/nhk16_files/entries.json
# sed 's/.aac/.mp3/g' input/nhk16_files/entries.json > output/mp3/user_files/nhk16_files/entries.json

# Build an index of the jpod files and remove duplicates
python "$SCRIPT_PATH/jpod_index.py"

# Convert jpod files
python "$SCRIPT_PATH/ffmpegmulti.py" --no-silence-remove opus temp/jpod output/opus/user_files/jpod_files --quality "-b:a 256k"
# python "$SCRIPT_PATH/ffmpegmulti.py" --no-silence-remove mp3 temp/jpod output/mp3/user_files/jpod_files
printf "{\n  \"type\": \"ajt_jp\"\n}\n" > output/opus/user_files/jpod_files/source_meta.json
# printf "{\n  \"type\": \"ajt_jp\"\n}\n" > output/mp3/user_files/jpod_files/source_meta.json

sed 's/.mp3/.opus/g' temp/jpod/index.json > output/opus/user_files/jpod_files/index.json
# cp temp/jpod/index.json output/mp3/user_files/jpod_files/index.json

# Generates jmdict_forms.json
refresh_source "JMdict_e"
python "$SCRIPT_PATH/parse_jmdict.py"

# # create final archives
# DATE="$(date -u +%Y-%m-%d)"
# #cd output/opus
# #7z a ../../local-yomichan-audio-"$DATE"-opus.7z user_files
# #cd ../mp3
# #7z a ../../local-yomichan-audio-"$DATE"-mp3.7z user_files
# #cd ../..
# tar --numeric-owner --sort=name -I"xz -T0" -cf local-yomichan-audio-collection-"$DATE"-opus.tar.xz -C output/opus user_files
# # tar --numeric-owner --sort=name -I"xz -T0" -cf local-yomichan-audio-collection-"$DATE"-mp3.tar.xz -C output/mp3 user_files
