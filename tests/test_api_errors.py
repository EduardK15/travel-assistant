"""Offline tests for Nuitee retries; no API keys or network required."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# hotel_service only needs BASE and HEADERS; supply harmless test values.
if 'config' not in sys.modules:
    fake_config = types.ModuleType('config')
    fake_config.BASE = 'https://example.invalid'
    fake_config.HEADERS = {'X-API-Key': 'test-only'}
    sys.modules['config'] = fake_config
import hotel_service
import requests


class ApiErrorTests(unittest.TestCase):
    def response(self, status, data=None):
        r = Mock()
        r.status_code = status
        r.json.return_value = data if data is not None else {'data': []}
        return r

    @patch.object(hotel_service.time, 'sleep')
    @patch.object(hotel_service.requests, 'request')
    def test_timeout_then_success(self, request, sleep):
        request.side_effect = [requests.exceptions.Timeout(), self.response(200, {'data': [1]})]
        self.assertEqual(hotel_service.api_request('GET', '/data/hotels'), {'data': [1]})
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once()

    @patch.object(hotel_service.time, 'sleep')
    @patch.object(hotel_service.requests, 'request')
    def test_three_timeouts_raise(self, request, sleep):
        request.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(requests.exceptions.Timeout):
            hotel_service.api_request('GET', '/data/hotels')
        self.assertEqual(request.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch.object(hotel_service.time, 'sleep')
    @patch.object(hotel_service.requests, 'request')
    def test_503_then_success(self, request, sleep):
        request.side_effect = [self.response(503), self.response(200, {'data': [2]})]
        self.assertEqual(hotel_service.api_request('GET', '/data/hotels'), {'data': [2]})
        self.assertEqual(request.call_count, 2)

    @patch.object(hotel_service.time, 'sleep')
    @patch.object(hotel_service.requests, 'request')
    def test_401_does_not_retry(self, request, sleep):
        request.return_value = self.response(401)
        with self.assertRaisesRegex(ValueError, 'ключ'):
            hotel_service.api_request('GET', '/data/hotels')
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()

    @patch.object(hotel_service.time, 'sleep')
    @patch.object(hotel_service.requests, 'request')
    def test_invalid_json_is_reported(self, request, sleep):
        r = self.response(200)
        r.json.side_effect = ValueError('invalid json')
        request.return_value = r
        with self.assertRaisesRegex(ValueError, 'некорректные данные'):
            hotel_service.api_request('GET', '/data/hotels')
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()

    @patch.object(hotel_service.time, 'sleep')
    @patch.object(hotel_service.requests, 'request')
    def test_429_after_retries(self, request, sleep):
        request.return_value = self.response(429)
        with self.assertRaisesRegex(ValueError, 'лимит'):
            hotel_service.api_request('GET', '/data/hotels')
        self.assertEqual(request.call_count, 3)


if __name__ == '__main__':
    unittest.main()
