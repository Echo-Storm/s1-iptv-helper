# test_xtream_client.py -- retry-with-backoff and plain-language error
# translation in _api_get(), and the live_stream_url format.

import unittest
from unittest import mock

import requests

from s1iptv.xtream_client import XtreamClient, NetworkError


def _response(status_code=200, json_data=None, json_raises=False):
    resp = mock.Mock()
    resp.status_code = status_code
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    else:
        resp.raise_for_status.side_effect = None
    if json_raises:
        resp.json.side_effect = ValueError("not json")
    else:
        resp.json.return_value = json_data
    return resp


class TestApiGetRetry(unittest.TestCase):
    def setUp(self):
        self.client = XtreamClient('https://fake.test', 'u', 'p')
        # Don't actually sleep between retries in tests.
        self.sleep_patcher = mock.patch('s1iptv.xtream_client.time.sleep')
        self.sleep_patcher.start()
        self.addCleanup(self.sleep_patcher.stop)

    def test_succeeds_immediately_on_first_try(self):
        with mock.patch('s1iptv.xtream_client.requests.get', return_value=_response(json_data=[1, 2, 3])) as m:
            result = self.client._api_get('get_live_categories')
        self.assertEqual(result, [1, 2, 3])
        self.assertEqual(m.call_count, 1)

    def test_retries_on_connection_error_then_succeeds(self):
        with mock.patch(
            's1iptv.xtream_client.requests.get',
            side_effect=[requests.exceptions.ConnectionError(), _response(json_data=[1])],
        ) as m:
            result = self.client._api_get('get_live_categories')
        self.assertEqual(result, [1])
        self.assertEqual(m.call_count, 2)

    def test_retries_on_timeout_then_succeeds(self):
        with mock.patch(
            's1iptv.xtream_client.requests.get',
            side_effect=[requests.exceptions.Timeout(), _response(json_data=[1])],
        ):
            result = self.client._api_get('get_live_categories')
        self.assertEqual(result, [1])

    def test_exhausting_retries_raises_network_error_not_raw_exception(self):
        with mock.patch(
            's1iptv.xtream_client.requests.get',
            side_effect=requests.exceptions.ConnectionError(),
        ) as m:
            with self.assertRaises(NetworkError):
                self.client._api_get('get_live_categories')
        self.assertEqual(m.call_count, 3, "should try MAX_RETRIES times total")

    def test_4xx_fails_immediately_without_retrying(self):
        with mock.patch('s1iptv.xtream_client.requests.get', return_value=_response(status_code=403)) as m:
            with self.assertRaises(NetworkError):
                self.client._api_get('get_live_categories')
        self.assertEqual(m.call_count, 1, "client errors shouldn't be retried")

    def test_5xx_does_retry(self):
        with mock.patch(
            's1iptv.xtream_client.requests.get',
            side_effect=[_response(status_code=500), _response(json_data=[1])],
        ) as m:
            result = self.client._api_get('get_live_categories')
        self.assertEqual(result, [1])
        self.assertEqual(m.call_count, 2)

    def test_unparseable_response_is_a_network_error_not_a_crash(self):
        with mock.patch('s1iptv.xtream_client.requests.get', return_value=_response(json_raises=True)):
            with self.assertRaises(NetworkError):
                self.client._api_get('get_live_categories')


class TestLiveStreamUrl(unittest.TestCase):
    def test_no_live_prefix_no_extension(self):
        client = XtreamClient('https://example.com', 'user', 'pass')
        self.assertEqual(client.live_stream_url(12345), 'https://example.com:443/user/pass/12345')


if __name__ == '__main__':
    unittest.main()
