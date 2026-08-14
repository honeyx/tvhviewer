# TVHviewer

More modern desktop client for [TVHeadend](https://tvheadend.org/). Watch and record live TV on PC.

**TVHviewer is a fork of [TVHplayer](https://github.com/mfat/tvhplayer) by mFat.**
See [NOTICE.md](NOTICE.md) for full credits and a summary of what changed in this fork.

![Screenshot](Screenshots/Screenshot_6.png)

## Features

- Live TV & radio playback
- Full program guide: all channels at once, with a scrollable timeline
  view and a newspaper-style column view
- Dark / Light color theme
- Favorites menu, separate from the full channel browser
- Local recording (saves to disk via VLC/ffmpeg) with remembered save location
- Server status, tuner signal strength, and video/audio format shown
  in the status bar
- Cross-platform (Linux, macOS, Windows) — this fork has mainly been
  tested on Linux (Zorin OS / Ubuntu)

## Install

### Debian/Ubuntu (.deb)
Download the latest `.deb` from [Releases](../../releases) and install:
```bash
sudo apt install ./tvhviewer_*.deb
```

### From source
```bash
git clone https://github.com/honeyx/tvhviewer.git
cd tvhviewer
python3 -m venv venv
source venv/bin/activate
pip install -r runtime-requirements.txt
pip install PyQt5
sudo apt install vlc   # native VLC library, not from pip
cd tvhplayer
python3 tvhplayer.py
```

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
This is the same license as the original TVHplayer project.
