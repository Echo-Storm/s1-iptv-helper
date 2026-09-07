"""
Xtream Codes API client for the IPTV provider.

Deliberately thin — one method per player_api.php action actually used by
this app. Credentials come from config.json (see load_config), never
hardcoded here (see docs/PROVIDER_NOTES.md for why that matters).
"""

import json
import os
from urllib.parse import urlencode

import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')


class ConfigError(RuntimeError):
    pass


def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        raise ConfigError(
            f"Missing {path}. Copy config.example.json to config.json and "
            f"fill in your IPTV username/password."
        )
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    for key in ('server', 'username', 'password'):
        if not cfg.get(key):
            raise ConfigError(f"config.json is missing required field: {key}")
    return cfg


def load_config_or_blank(path=CONFIG_PATH):
    """Same as load_config, but returns blank values instead of raising when
    the file is missing or incomplete — for the Settings tab, which needs to
    render even before the app is configured."""
    blank = {'server': '', 'username': '', 'password': '', 'export_path': ''}
    if not os.path.exists(path):
        return blank
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return blank
    blank.update({k: cfg.get(k, '') for k in blank})
    return blank


def save_config(server, username, password, export_path=None, path=CONFIG_PATH):
    """export_path=None leaves whatever was already saved untouched (so
    saving connection settings doesn't wipe out a previously chosen export
    path, and vice versa)."""
    if export_path is None:
        export_path = load_config_or_blank(path).get('export_path', '')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(
            {'server': server, 'username': username, 'password': password, 'export_path': export_path},
            f, indent=2,
        )


def classify_url(url):
    """Return 'movie', 'series', or 'live' based on the stream URL shape."""
    u = url.lower()
    if '/movie/' in u:
        return 'movie'
    if '/series/' in u:
        return 'series'
    return 'live'


class XtreamClient:
    def __init__(self, server, username, password, timeout=30):
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.api_url = f"{self.server}/player_api.php"

    @classmethod
    def from_config(cls, path=CONFIG_PATH):
        cfg = load_config(path)
        return cls(cfg['server'], cfg['username'], cfg['password'])

    def _api_get(self, action, extra_params=None):
        params = {'username': self.username, 'password': self.password, 'action': action}
        if extra_params:
            params.update(extra_params)
        url = f"{self.api_url}?{urlencode(params)}"
        resp = requests.get(url, headers={'User-Agent': 'S1IptvHelper/1.0'}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ---- Live -------------------------------------------------------
    def get_live_categories(self):
        """List of {category_id, category_name, parent_id}."""
        data = self._api_get('get_live_categories')
        if not isinstance(data, list):
            raise ValueError('Unexpected response from get_live_categories')
        return data

    def get_live_streams(self, category_id=None):
        params = {'category_id': category_id} if category_id is not None else None
        data = self._api_get('get_live_streams', params)
        if not isinstance(data, list):
            raise ValueError('Unexpected response from get_live_streams')
        return data

    # ---- VOD (movies) -------------------------------------------------
    def get_vod_categories(self):
        data = self._api_get('get_vod_categories')
        if not isinstance(data, list):
            raise ValueError('Unexpected response from get_vod_categories')
        return data

    def get_vod_streams(self, category_id=None):
        params = {'category_id': category_id} if category_id is not None else None
        data = self._api_get('get_vod_streams', params)
        if not isinstance(data, list):
            raise ValueError('Unexpected response from get_vod_streams')
        return data

    # ---- Series ---------------------------------------------------------
    def get_series_categories(self):
        data = self._api_get('get_series_categories')
        if not isinstance(data, list):
            raise ValueError('Unexpected response from get_series_categories')
        return data

    def get_series(self, category_id=None):
        params = {'category_id': category_id} if category_id is not None else None
        data = self._api_get('get_series', params)
        if not isinstance(data, list):
            raise ValueError('Unexpected response from get_series')
        return data

    # ---- Convenience ------------------------------------------------
    def live_stream_url(self, stream_id):
        """
        No /live/ prefix and no extension -- confirmed against a live fetch
        of this provider's own m3u_plus export (2026-09-06):
          https://blueonesuperoceanhere.com:443/{user}/{pass}/{stream_id}
        This differs from the generic Xtream Codes convention (which usually
        has /live/ and a .ts/.m3u8 extension) -- don't "fix" this to match
        the generic pattern without re-verifying against a real fetch first.
        """
        return f"{self.server}:443/{self.username}/{self.password}/{stream_id}"

    def movie_stream_url(self, vod_id, ext='mp4'):
        return f"{self.server}/movie/{self.username}/{self.password}/{vod_id}.{ext}"

    def series_stream_url(self, episode_id, ext='mp4'):
        return f"{self.server}/series/{self.username}/{self.password}/{episode_id}.{ext}"
