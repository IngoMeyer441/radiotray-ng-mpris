# Radiotray-NG MPRIS

## Overview

Radiotray-NG MPRIS is a wrapper for [Radiotray-NG](https://github.com/ebruck/radiotray-ng) to add an [MPRIS2
interface](https://specifications.freedesktop.org/mpris-spec/latest/) which integrates well with desktop environments
(like [GNOME](https://extensions.gnome.org/extension/1379/mpris-indicator-button/),
[KDE](https://community.kde.org/MPRIS) or [XFCE](https://docs.xfce.org/panel-plugins/xfce4-pulseaudio-plugin/start)) or
desktop independent music player control tools like [playerctl](https://github.com/altdesktop/playerctl).

## Installation

First, you need a working installation of [Radiotray-NG](https://github.com/ebruck/radiotray-ng).

Radiotray-NG MPRIS is available on PyPI and can be installed with `pip`:

```bash
python3 -m pip install radiotray-ng-mpris
```

Please note that at least Python 3.10 is required (because of its dependency
[`mpris_server`](https://pypi.org/project/mpris-server/)). You can check your installed Python version with

```bash
python3 --version
```

If your Python version is too old, you don't want to use `pip` for the installation or you don't care about Python at
all, you can also download self-contained executables (no Python installation required) for Linux x64 from the [releases
page](https://github.com/IngoMeyer441/radiotray-ng-mpris/releases).

If you run an Arch-based system, you can also install Radiotray-NG MPRIS from the
[AUR](https://aur.archlinux.org/packages/radiotray-ng-mpris/):

```bash
yay -S radiotray-ng-mpris
```

In this case, Radiotray-NG will be installed as a package dependency automatically.

## Usage

Run

```bash
radiotray-ng-mpris
```

on the command line (or any application finder) to start Radiotray-NG and the MPRIS2 integration. Any MPRIS2 control
interface should start working with Radiotray-NG immediately.

Exit the application by quitting Radiotray-NG or the wrapper script (press `<Ctrl-c>` on the command line).

## Command line options

```text
usage: radiotray-ng-mpris [-h] [-p] [-V]
                          [-q | --error | --warn | -v | --debug]

radiotray-ng-mpris is a wrapper script for radiotray-ng to provide an MPRIS2
interface.

options:
  -h, --help     show this help message and exit
  -p, --play     start playback immediately
  -V, --version  print the version number and exit
  -q, --quiet    be quiet (default: "False")
  --error        print error messages (default: "False")
  --warn         print warning and error messages (default: "True")
  -v, --verbose  be verbose (default: "False")
  --debug        print debug messages (default: "False")
```
