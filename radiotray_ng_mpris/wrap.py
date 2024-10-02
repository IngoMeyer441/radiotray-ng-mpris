import json
import logging
import os
import signal
import subprocess
import sys
import time
from pprint import pformat
from types import FrameType
from typing import Optional, cast

import pydbus
from gi.repository import GLib
from mpris_server.adapters import ActivePlaylist, MprisAdapter
from mpris_server.base import (
    DEFAULT_DESKTOP,
    DEFAULT_ORDERINGS,
    DEFAULT_PLAYLIST_COUNT,
    DEFAULT_RATE,
    MIME_TYPES,
    URI,
    DbusObj,
    Microseconds,
    Paths,
    PlaylistEntry,
    PlayState,
    Track,
)
from mpris_server.events import EventAdapter
from mpris_server.mpris.metadata import DEFAULT_METADATA, Metadata, MetadataObj, ValidMetadata
from mpris_server.server import Server

try:
    from mpris_server.base import Rate, Volume
except ImportError:
    from mpris_server.base import RateDecimal as Rate
    from mpris_server.base import VolumeDecimal as Volume

MAX_DBUS_GET_TRY_COUNT = 30
RADIOTRAY_NG_DEFAULT_POLL_INTERVAL = 1000  # ms


logger = logging.getLogger(__name__)
radiotray_ng_process = None


class RadiotrayNgApi:
    def __init__(self) -> None:
        self._session_bus = pydbus.SessionBus()
        try_count = 0
        while True:
            try:
                self._radiotray_ng_dbus_obj = self._session_bus.get(
                    "com.github.radiotray_ng", "/com/github/radiotray_ng"
                )
                break
            except GLib.GError as e:
                try_count += 1
                if not (
                    e.message.startswith("GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown")
                    and try_count < MAX_DBUS_GET_TRY_COUNT
                ):
                    raise
                time.sleep(1)
        self._radiotray_ng_dbus_api = self._radiotray_ng_dbus_obj["com.github.radiotray_ng"]

    def get_bookmarks(self) -> dict[str, bool | str | int]:
        logger.debug('Calling "get_bookmarks" of the radiotray_ng api')
        bookmarks: dict[str, bool | str | int] = json.loads(self._radiotray_ng_dbus_api.get_bookmarks())
        logger.debug("Bookmarks:\n%s", pformat(bookmarks))
        return bookmarks

    def get_config(self) -> list[dict[str, str | list[dict[str, str]]]]:
        logger.debug('Calling "get_config" of the radiotray_ng api')
        config: list[dict[str, str | list[dict[str, str]]]] = json.loads(self._radiotray_ng_dbus_api.get_config())
        logger.debug("Config:\n%s", pformat(config))
        return config

    def get_player_state(self) -> dict[str, bool | str]:
        logger.debug('Calling "get_player_state" of the radiotray_ng api')
        player_state: dict[str, bool | str] = json.loads(self._radiotray_ng_dbus_api.get_player_state())
        logger.debug("Player state:\n%s", pformat(player_state))
        return player_state

    def mute(self) -> None:
        logger.debug('Calling "mute" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.mute()

    def next_station(self) -> None:
        logger.debug('Calling "next_station" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.next_station()

    def play(self) -> None:
        logger.debug('Calling "play" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.play()

    def play_station(self, group: str, station: str) -> None:
        logger.debug('Calling "play_station" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.play_station(group, station)

    def play_url(self, url: str) -> None:
        logger.debug('Calling "play_url" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.play_url(url)

    def previous_station(self) -> None:
        logger.debug('Calling "previous_station" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.previous_station()

    def quit(self) -> None:
        logger.debug('Calling "quit" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.quit()

    def reload_bookmarks(self) -> None:
        logger.debug('Calling "reload_bookmarks" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.reload_bookmarks()

    def set_volume(self, level: int) -> None:
        logger.debug('Calling "set_volume" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.set_volume(str(level))

    def stop(self) -> None:
        logger.debug('Calling "stop" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.stop()

    def volume_down(self) -> None:
        logger.debug('Calling "volume_down" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.volume_down()

    def volume_up(self) -> None:
        logger.debug('Calling "volume_up" of the radiotray_ng api')
        self._radiotray_ng_dbus_api.volume_up()


class RadiotrayNgMprisAdapter(MprisAdapter):  # type: ignore
    def __init__(self, radiotray_ng_api: RadiotrayNgApi) -> None:
        super().__init__()
        self._radiotray_ng_api = radiotray_ng_api

    def can_quit(self) -> bool:
        return True

    def can_raise(self) -> bool:
        return False

    def can_fullscreen(self) -> bool:
        return False

    def has_tracklist(self) -> bool:
        return False

    def get_uri_schemes(self) -> list[str]:
        return cast(list[str], URI)

    def get_mime_types(self) -> list[str]:
        return cast(list[str], MIME_TYPES)

    def set_raise(self, val: bool) -> None:
        pass

    def quit(self) -> None:
        self._radiotray_ng_api.quit()

    def get_fullscreen(self) -> bool:
        return False

    def set_fullscreen(self, val: bool) -> None:
        pass

    def get_desktop_entry(self) -> Paths:
        return DEFAULT_DESKTOP

    def metadata(self) -> ValidMetadata:
        """
        Implement this function to supply your own MPRIS Metadata.

        If this function is implemented, metadata won't be built from get_current_track().

        See: https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/
        """
        player_state = self._radiotray_ng_api.get_player_state()
        return MetadataObj(
            art_url=player_state["image"],
            url=player_state["url"],
            title=player_state["title"],
            artists=[player_state["artist"]],
            comments=["Radio Station: {}".format(player_state["station"])],
        )

    def get_current_track(self) -> Track:
        """
        This function is an artifact of forking the base MPRIS library to a generic interface.
        The base library expected Track-like objects to build metadata.

        If metadata() is implemented, this function won't be used to build MPRIS metadata.
        """
        pass

    def get_current_position(self) -> Microseconds:
        return 0

    def next(self) -> None:
        self._radiotray_ng_api.next_station()

    def previous(self) -> None:
        self._radiotray_ng_api.previous_station()

    def pause(self) -> None:
        self._radiotray_ng_api.stop()

    def resume(self) -> None:
        self._radiotray_ng_api.play()

    def stop(self) -> None:
        self._radiotray_ng_api.stop()

    def play(self) -> None:
        self._radiotray_ng_api.play()

    def get_playstate(self) -> PlayState:
        player_state = self._radiotray_ng_api.get_player_state()
        if player_state["state"] == "playing":
            return PlayState.PLAYING
        else:
            return PlayState.STOPPED

    def seek(self, time: Microseconds, track_id: Optional[DbusObj] = None) -> None:
        pass

    def open_uri(self, uri: str) -> None:
        self._radiotray_ng_api.play_url(uri)

    def is_repeating(self) -> bool:
        return False

    def is_playlist(self) -> bool:
        return False

    def set_repeating(self, val: bool) -> None:
        pass

    def set_loop_status(self, val: str) -> None:
        pass

    def get_rate(self) -> Rate:
        return DEFAULT_RATE

    def set_rate(self, val: Rate) -> None:
        pass

    def set_minimum_rate(self, val: Rate) -> None:
        pass

    def set_maximum_rate(self, val: Rate) -> None:
        pass

    def get_minimum_rate(self) -> Rate:
        return DEFAULT_RATE

    def get_maximum_rate(self) -> Rate:
        return DEFAULT_RATE

    def get_shuffle(self) -> bool:
        return False

    def set_shuffle(self, val: bool) -> None:
        pass

    def get_art_url(self, track: int) -> str:
        return ""

    def get_volume(self) -> Volume:
        return float(self._radiotray_ng_api.get_player_state()["volume"]) / 100

    def set_volume(self, val: Volume) -> None:
        self._radiotray_ng_api.set_volume(int(val * 100))

    def is_mute(self) -> bool:
        return bool(self._radiotray_ng_api.get_player_state()["mute"])

    def set_mute(self, val: bool) -> None:
        if val != self.is_mute():
            self._radiotray_ng_api.mute()

    def can_go_next(self) -> bool:
        return True

    def can_go_previous(self) -> bool:
        return True

    def can_play(self) -> bool:
        return True

    def can_pause(self) -> bool:
        return True

    def can_seek(self) -> bool:
        return False

    def can_control(self) -> bool:
        return True

    def get_stream_title(self) -> str:
        return ""

    def get_previous_track(self) -> Track:
        return Track("")

    def get_next_track(self) -> Track:
        return Track("")

    def activate_playlist(self, id: DbusObj) -> None:
        pass

    def get_playlists(self, index: int, max_count: int, order: str, reverse: bool) -> list[PlaylistEntry]:
        # TODO
        return []

    def get_playlist_count(self) -> int:
        return cast(int, DEFAULT_PLAYLIST_COUNT)

    def get_orderings(self) -> list[str]:
        return cast(list[str], DEFAULT_ORDERINGS)

    def get_active_playlist(self) -> ActivePlaylist:
        # TODO
        pass

    def get_tracks_metadata(self, track_ids: list[DbusObj]) -> Metadata:
        return DEFAULT_METADATA

    def add_track(self, uri: str, after_track: DbusObj, set_as_current: bool) -> None:
        pass

    def remove_track(self, track_id: DbusObj) -> None:
        pass

    def go_to(self, track_id: DbusObj) -> None:
        pass

    def get_tracks(self) -> list[DbusObj]:
        # TODO
        return []

    def can_edit_tracks(self) -> bool:
        return False


class RadiotrayNgEventAdapter:
    def __init__(
        self,
        radiotray_ng_api: RadiotrayNgApi,
        radiotray_ng_mpris_adapter: RadiotrayNgMprisAdapter,
        poll_interval: int = RADIOTRAY_NG_DEFAULT_POLL_INTERVAL,
    ):
        self._radiotray_ng_api = radiotray_ng_api
        self._mpris_server = Server("Radiotray-NG", adapter=radiotray_ng_mpris_adapter)
        self._event_adapter = EventAdapter(root=self._mpris_server.root, player=self._mpris_server.player)
        self._previous_player_state: Optional[dict[str, bool | str]] = None
        self._enable_event_polling(poll_interval)

    def _enable_event_polling(self, poll_interval: int) -> None:
        def check_radiotray_state() -> bool:
            def get_changed_state_attributes() -> dict[str, bool | str]:
                player_state = self._radiotray_ng_api.get_player_state()
                if self._previous_player_state is None:
                    self._previous_player_state = player_state
                    return {}
                changed_state_attributes = {
                    key: value for key, value in player_state.items() if value != self._previous_player_state.get(key)
                }
                self._previous_player_state = player_state
                return changed_state_attributes

            def on_changed_artist(artist: str) -> None:
                logger.debug('Changed artist: "%s"', artist)
                self._event_adapter.on_title()

            def on_changed_bitrate(bitrate: str) -> None:
                logger.debug('Changed bitrate: "%s"', bitrate)

            def on_changed_codec(codec: str) -> None:
                logger.debug('Changed codec: "%s"', codec)

            def on_changed_group(group: str) -> None:
                logger.debug('Changed group: "%s"', group)

            def on_changed_image(image: str) -> None:
                logger.debug('Changed image: "%s"', image)

            def on_changed_mute(mute: bool) -> None:
                logger.debug('Changed mute: "%s"', str(mute))
                self._event_adapter.on_volume()

            def on_changed_state(state: str) -> None:
                logger.debug('Changed state: "%s"', state)
                if state == "stopped":
                    self._event_adapter.on_playpause()
                elif state == "playing":
                    self._event_adapter.on_playback()

            def on_changed_station(station: str) -> None:
                logger.debug('Changed station: "%s"', station)

            def on_changed_title(title: str) -> None:
                logger.debug('Changed title: "%s"', title)
                self._event_adapter.on_title()

            def on_changed_url(url: str) -> None:
                logger.debug('Changed url: "%s"', url)

            def on_changed_volume(volume: str) -> None:
                logger.debug('Changed volume: "%s"', volume)
                self._event_adapter.on_volume()

            # Terminate if the Radiotray-NG process was terminated by the user
            if radiotray_ng_process is None or radiotray_ng_process.poll() is not None:
                logging.info("Radiotray-NG process terminated -> exit")
                os.kill(os.getpid(), signal.SIGINT)
                return False
            changed_state_attributes = get_changed_state_attributes()
            if changed_state_attributes:
                logger.info("Changed state attributes:\n%s", pformat(changed_state_attributes))
            for key, value in changed_state_attributes.items():
                potential_func_name = f"on_changed_{key}"
                if potential_func_name in locals() and callable(locals()[potential_func_name]):
                    locals()[potential_func_name](value)

            return True  # Schedule a new timeout event

        GLib.timeout_add(poll_interval, check_radiotray_state)

    def publish_and_loop(self) -> None:
        self._mpris_server.loop()


def start_radiotray_ng(play: bool) -> subprocess.Popen[str]:
    global radiotray_ng_process

    args = ["radiotray-ng"]
    if play:
        args.append("--play")
    radiotray_ng_process = subprocess.Popen(args, universal_newlines=True)
    return radiotray_ng_process


def setup_signal_handling() -> None:
    def handle_sigint_sigterm(sig: int, frame: Optional[FrameType]) -> None:
        logger.debug("Got signal %s", signal.Signals(sig).name)
        if radiotray_ng_process is not None and radiotray_ng_process.poll() is None:
            logger.info("Send a quit request to Radiotray NG")
            try:
                RadiotrayNgApi().quit()
            except GLib.GError:
                # Quiting without replying DBus queries raises an GError
                pass
            logger.info("Waiting for the process to quit...")
            radiotray_ng_process.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint_sigterm)
    signal.signal(signal.SIGTERM, handle_sigint_sigterm)


def wrap_radiotray_ng(play: bool) -> None:
    start_radiotray_ng(play)
    radiotray_ng_api = RadiotrayNgApi()
    radiotray_ng_mpris_adapter = RadiotrayNgMprisAdapter(radiotray_ng_api)
    radiotray_ng_event_adapter = RadiotrayNgEventAdapter(radiotray_ng_api, radiotray_ng_mpris_adapter)
    radiotray_ng_event_adapter.publish_and_loop()
