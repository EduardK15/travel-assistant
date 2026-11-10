"""Offline integration tests for Travel Assistant 2.8. Run: python -m unittest discover -s tests -v"""
import sys
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

# The app imports API-backed modules at startup. Replace them before importing app,
# so tests never ask for credentials or make network calls.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
fake_ai = types.ModuleType('ai_service')
fake_ai.interpret = lambda query: {'city': 'Haifa', 'limit': 3, 'sort_by': 'price'}
fake_hotels = types.ModuleType('hotel_service')
fake_hotels.fetch_catalog = lambda city: {'1': {'id': '1'}}
fake_hotels.fetch_rates = lambda catalog, checkin, checkout, adults: ([], True)
sys.modules['ai_service'] = fake_ai
sys.modules['hotel_service'] = fake_hotels

import app as travel_app


class TravelAssistantTests(unittest.TestCase):
    def setUp(self):
        self.client = travel_app.app.test_client()
        self.checkin = (date.today() + timedelta(days=14)).isoformat()
        self.checkout = (date.today() + timedelta(days=16)).isoformat()
        self.data = {'query': 'Найди 3 гостиницы в Хайфе', 'checkin': self.checkin,
                     'checkout': self.checkout, 'adults': '2', 'max_price': '',
                     'sort_by': 'price', 'min_stars': '0'}
        travel_app.RESULTS.clear()

    def post(self, **changes):
        return self.client.post('/search', data={**self.data, **changes})

    def test_checkout_must_follow_checkin(self):
        response = self.post(checkout=self.checkin)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(travel_app.RESULTS), 0)

    def test_negative_budget_is_rejected(self):
        response = self.post(max_price='-100')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(travel_app.RESULTS), 0)

    def test_zero_budget_is_rejected(self):
        response = self.post(max_price='0')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(travel_app.RESULTS), 0)

    def test_hotels_sorted_by_ascending_price(self):
        hotels = [
            {'name': 'Expensive', 'price': 500, 'currency': 'ILS', 'stars': 4, 'image_url': None},
            {'name': 'Cheap', 'price': 300, 'currency': 'ILS', 'stars': 3, 'image_url': None},
            {'name': 'Middle', 'price': 400, 'currency': 'ILS', 'stars': 5, 'image_url': None},
        ]
        with patch.object(travel_app, 'fetch_rates', return_value=(hotels, True)):
            response = self.post()
        self.assertEqual(response.status_code, 303)
        saved = next(iter(travel_app.RESULTS.values()))['context']['hotels']
        self.assertEqual([h['price'] for h in saved], [300, 400, 500])

    def test_empty_results_are_handled(self):
        with patch.object(travel_app, 'fetch_rates', return_value=([], True)):
            response = self.post()
        self.assertEqual(response.status_code, 303)
        saved = next(iter(travel_app.RESULTS.values()))['context']['hotels']
        self.assertEqual(saved, [])
        result_page = self.client.get(response.headers['Location'])
        self.assertEqual(result_page.status_code, 200)


if __name__ == '__main__':
    unittest.main()
