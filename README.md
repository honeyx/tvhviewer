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
- Launch Kodi from the app (File menu / toolbar, path under Settings →
  Kodi Path): live TV pauses while Kodi runs and resumes when it closes
- Optional on-screen display (OSD) drawn from skins you provide yourself, with
  Media Center style keys (see below)
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

### Windows (installer)
Download the latest `tvhviewer-X.X.X-setup.exe` from [Releases](../../releases)
and run it. ffmpeg (for local recording) is bundled — you only need
**[VLC](https://www.videolan.org/vlc/) installed separately**, since
python-vlc only provides bindings to your system's VLC installation,
not VLC itself.

### macOS (built executable)
Download the latest macOS build from [Releases](../../releases).
**You still need [VLC](https://www.videolan.org/vlc/) installed separately**,
and **[ffmpeg](https://ffmpeg.org/download.html)** on your PATH for local
recording (server-side recording via the EPG guide doesn't need it).

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

## OSD skins (optional)

TVHviewer can draw an on-screen display (volume bar, clock, channel/now-next
info) from skins in the XML "OSDSkin 1.1" layout. **No skins are included.**
Copy a skin folder you are entitled to use into the `OSDskins` folder
(Settings → OSD Skin → *Open OSDskins Folder*; located in the TVHviewer config
directory, e.g. `%APPDATA%\TVHplayer\OSDskins` on Windows) and pick it under
Settings → OSD Skin. The default is *Off*.

Key bindings: Settings → *Keyboard / Remote Keys...* lets you assign keys by
pressing them (a remote or Flirc just sends key presses) and can import a
`.remote` profile file; changes apply immediately. The defaults follow a typical
remote profile: `Ctrl+D` info, `Ctrl+G`/`E` program guide, `K` channel list,
`M` mute, volume keys, `+`/`-` channel up/down, `PgUp`/`PgDown` next/previous
favourite, `0`-`9` direct channel entry, `Alt+Enter` fullscreen.
