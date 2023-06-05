# local-audio-yomichan-build-scripts

A collection of small scripts to mass-process audio files from the
[Local Audio Server for Yomichan](https://github.com/themoeway/local-audio-yomichan)
Anki Add-on.

Goals of this repo:
- Normalize the audio
- Remove silence from the front and back of audio
- Convert all audio to opus / mp3 (opus for more efficient storage of files, mp3 for better compatibility with AnkiMobile)
- Remove broken and duplicate files:
    - Remove JPod audio that has different readings mapping to the same audio file
    - Remove a few audio files that simply didn't have the correct word audio in the first place
- Create `jmdict_forms.json` for post processing work after creating the entire database

NON-Goals:
- Reduce the quality of the audio for the sake of more efficient storage

## Expected File Structure
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

## Prerequisites
This requires a Unix system to run. On Windows, you can use [WSL](https://learn.microsoft.com/en-US/windows/wsl/about).

Dependencies:
- ffmpeg >= 6.0 (one that can decode aac/mp3, and can encode mp3/opus)
- python (3.11+)

## Usage
1. Download the original audio files.
1. Run the following command:
    ```
    ./build-collection.sh
    ```


## TODO
- (done) run ffmpegmulti on all forvo audio and shinmeikai8 audio
- (done) remove exact duplicates within the `jpod` and `jpod_alternate` sources, unify it as one, and build an index (done via `jpod_index.py`)
- (done?) make all scripts use the unified file directory structure
- (done) run `ffmpegmulti --no-silence-remove` on `jpod` and `jpod_alternate`
- (done) convert `nhk16_files` to opus and to mp3. Decide if they need normalization and/or silence removal (norm + silence it is)
- (done) remove broken files:
    - (done) skent/解く - just rm from the build script
    - (done) broken jpod files (https://discord.com/channels/617136488840429598/1074057444365443205/1113679859609260062)
        - (done) Filter these out in the `jpod_index` script
- (done) use jmdict word alternatives to map audio to more words (i.e. all of 手すり・手摺り・手摺 should have the same audio)
    - the alternatives data should be available to the add-on, not to this repo (as it would be part of creating the main database?)
    - see `yomichan_import` / JMdict forms dictionary for reference on parsing the original xml
- (done) main build script (`build_collection.sh`)
- (done) rename repo
- (done) investigate how much `opus` actually reduces file size for all sources! SMK8 might not have much of an effect
    > for shinmeikai, i initially converted all the files to opus, but decided to keep them in the original format after measuring file sizes and noticing no improvement in size.
    - It should suffice to just compare the mp3 and opus outputs when it's all done
- (done) get more data for normalization (sentence audio data, compare with output)

## Credits
None of this would have even existed if it wasn't for the ideas and work from these fantastic people:

* **[@Mansive](https://github.com/Mansive)**:
    - Original author of `ffmpegmulti.py`
    - Jump-started this project entirely by noting that Forvo audio can be improved via mass processed
* **[@tsweet64](https://github.com/tsweet64)**:
    - Added `opus` and `mp3` support
    - Created the general build script
    - Pointed out that most JPod files were duplicates

There's a lot more stuff that these two did that isn't mentioned here, either because I forgot or it would make the list a bit too long. Thanks again!


<!--
Original discussions (TMW Server)
* https://discord.com/channels/617136488840429598/1111699416701730871/1111699416701730871
* https://discord.com/channels/617136488840429598/1074057444365443205/1112936831013617724
-->

