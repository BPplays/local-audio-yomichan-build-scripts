# local-audio-yomichan-build-scripts

A collection of small scripts to mass-process audio files from the
[Local Audio Server for Yomichan](https://github.com/themoeway/local-audio-yomichan)
Anki Add-on.

Goals of this repo:
- Normalize the audio
- Remove silence from the front and back of audio
- Convert all audio to opus / mp3 (opus for more efficient storage of files, mp3 for better compatibility with AnkiMobile)
- Remove broken and duplicate files

## Expected File Structure (WIP)
```
(repo-root)
 L input
    L forvo_files
    L jpod_files
    L jpod_alt_files
    L nhk16_files
    L shinmeikai8_files
 L output
    L opus
       L user_files
          L ...
    L mp3
       L user_files
          L ...
    L ...
```


## TODO
- (done) run ffmpegmulti on all forvo audio and shinmeikai8 audio
- (done) remove exact duplicates between `jpod` and `jpod_alternate` via `compare.py delete`
- decide on unified file directory structure
- do something to organize the rest of the files and different word duplicates (build a AJT style index?)
- run `ffmpegmulti --no-silence-remove` on `jpod` and `jpod_alternate`
- convert `nhk16_files` to opus and to mp3
- remove broken files:
    - skent/解く
    - broken jpod files (https://discord.com/channels/617136488840429598/1074057444365443205/1113679859609260062)
- (maybe?) use jmdict word alternatives to map audio to more words (i.e. all of 手すり・手摺り・手摺 should have the same audio)
    - the alternatives data should be available to the add-on, not to this repo (as it would be part of creating the main database?)
    - see `yomichan_import` / JMdict forms dictionary for reference on parsing the original xml
- main build script (started: `DRAFT_build_collection.sh`)
- rename repo

## Credits
- TODO
