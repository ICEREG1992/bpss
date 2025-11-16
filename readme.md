# BPSS
Burnout Paradise Song Switcher. Easy-to-use GUI for modifying song data and audio for Burnout Paradise. Works for both Remastered and The Ultimate Box.

![Screenshot of BPSS software](image.png)

Requires [sx](https://burnout.wiki/wiki/Sounds_(Burnout_Paradise)) and [YAP](https://github.com/burninrubber0/YAP).

## How to Setup
Just point BPSS at your install folder for Burnout Paradise, your sx.exe file, and your YAP.exe file.

If you are on Windows 8.1 or earlier, please install the [Visual Studio 2015 C++ Redistributable](https://www.microsoft.com/en-gb/download/details.aspx?id=48145).

## How to Use
Make your desired soundtrack changes in the table, save it to a file, then press Apply to apply those changes to your game. Press Unapply to revert all changes, and Reset to reset the table back to defaults, or to your currently loaded file.

BPSS supports the same formats as sx, which includes .wav, .aiff, and .mp3 (mpga), and maybe others. **.ogg, .flac, and .mp3 (mp4a) are NOT supported.**

Cells with matching background colors are **synced**, which means they use the same string variable. In the future, you will be able to disambiguate these synced boxes (at the risk of crashing).

## How to build

```python
pip install -r requirements.txt
pyinstaller BPSS.spec
```