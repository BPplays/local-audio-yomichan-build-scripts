# ffmpegmulti

A simple script that runs ffmpeg on multiple audio files.
The goal of this script is to mass-process audio files from the
[Local Audio Server for Yomichan](https://github.com/themoeway/local-audio-yomichan) Anki Add-on
in order to:
- Normalize the audio
- Remove silence from the front and back of audio

## Changes that should be done to the original audio
- (done) run ffmpegmulti on all forvo audio and shinmeikai8 audio
- (done) remove exact duplicates between `jpod` and `jpod_alternate` via `compare.py delete`
- do something to organize the rest of the files and different word duplicates (build a AJT style index?)
- run `ffmpegmulti --no-silence-remove` on `jpod` and `jpod_alternate`
- convert `nhk16_files` to opus and to mp3
- remove skent/解く
- remove broken jpod files

## Credits
- TODO
