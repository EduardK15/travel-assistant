from urllib.parse import urlparse
import requests
import logging
import time
from config import BASE, HEADERS

logger = logging.getLogger(__name__)
RETRYABLE_STATUS = {429, 502, 503, 504}
MAX_ATTEMPTS = 3


def api_request(method, path, **kwargs):
    """Retry transient Nuitee search failures, never log credentials or request bodies."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.request(
                method, BASE + path, headers=HEADERS, timeout=(5, 15), **kwargs
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            logger.warning('Nuitee connection failure: endpoint=%s attempt=%s/%s type=%s',
                           path, attempt, MAX_ATTEMPTS, type(exc).__name__)
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(0.5 * attempt)
            continue

        status = response.status_code
        if status in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
            logger.warning('Nuitee temporary HTTP error: endpoint=%s status=%s attempt=%s/%s',
                           path, status, attempt, MAX_ATTEMPTS)
            time.sleep(0.5 * attempt)
            continue
        if status in (401, 403):
            raise ValueError('Nuitee отклонил ключ или доступ к этому API.')
        if status == 429:
            raise ValueError('Превышен лимит запросов Nuitee. Повторите позже.')
        if status == 204:
            return {'data': []}
        if status != 200:
            raise ValueError(f'Nuitee вернул HTTP {status}.')
        try:
            return response.json()
        except ValueError as exc:
            logger.warning('Nuitee invalid JSON: endpoint=%s', path)
            raise ValueError('Nuitee вернул некорректные данные. Попробуйте позже.') from exc



def fetch_catalog(city):
    payload = api_request('GET', '/data/hotels', params={
        'countryCode': 'IL', 'cityName': city, 'limit': 40})
    hotels = payload.get('data', [])
    if not isinstance(hotels, list):
        raise ValueError('Неверный формат каталога Nuitee.')
    return {str(h['id']): h for h in hotels if isinstance(h, dict) and h.get('id')}


def parse_stars(value):
    try:
        number = int(value)
        return number if 1 <= number <= 5 else None
    except (TypeError, ValueError):
        return None


def safe_photo_url(value):
    """Use only explicit HTTPS image URLs supplied by the hotel provider."""
    if not isinstance(value, str) or len(value) > 2000:
        return None
    try:
        parsed = urlparse(value.strip())
        if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
            return value.strip()
    except ValueError:
        pass
    return None


def find_photo(hotel):
    """Conservative discovery: no invented images and no unrelated API requests."""
    if not isinstance(hotel, dict):
        return None
    # Provider schemas can vary. Look for common, explicit image fields only.
    for field in ('mainPhoto', 'mainImage', 'thumbnail', 'imageUrl', 'photoUrl'):
        value = hotel.get(field)
        if isinstance(value, dict):
            value = value.get('url') or value.get('src')
        url = safe_photo_url(value)
        if url:
            return url
    for field in ('hotelImages', 'images', 'photos'):
        items = hotel.get(field)
        if isinstance(items, list):
            for item in items[:8]:
                if isinstance(item, dict):
                    item = item.get('url') or item.get('src') or item.get('imageUrl')
                url = safe_photo_url(item)
                if url:
                    return url
    return None


def fetch_rates(catalog, checkin, checkout, adults):
    body = {'hotelIds': list(catalog), 'checkin': checkin, 'checkout': checkout,
            'currency': 'ILS', 'guestNationality': 'IL',
            'occupancies': [{'adults': adults}], 'maxRatesPerHotel': 1,
            'includeHotelData': True}
    payload = api_request('POST', '/hotels/rates', json=body)
    if payload.get('error'):
        code = payload['error'].get('code') if isinstance(payload['error'], dict) else None
        if code == 2001:
            return [], bool(payload.get('sandbox'))
        raise ValueError('Nuitee сообщил об ошибке при поиске цен.')
    results = []
    extra = {str(h.get('id')): h for h in payload.get('hotels', []) if isinstance(h, dict)}
    for item in payload.get('data', []):
        if not isinstance(item, dict):
            continue
        hotel_id = str(item.get('hotelId', ''))
        info = catalog.get(hotel_id) or extra.get(hotel_id) or {}
        offers = []
        for room in item.get('roomTypes', []):
            if not isinstance(room, dict):
                continue
            for rate in room.get('rates', []):
                if not isinstance(rate, dict):
                    continue
                total = (rate.get('retailRate') or {}).get('total') or []
                if total and isinstance(total[0], dict):
                    value = total[0].get('amount')
                    currency = total[0].get('currency', 'ILS')
                    if isinstance(value, (int, float)) and value >= 0:
                        offers.append((float(value), currency))
        if offers:
            price, currency = min(offers, key=lambda p: p[0])
            results.append({'name': info.get('name') or 'Гостиница ' + hotel_id,
                            'address': info.get('address') or 'Адрес не указан',
                            'price': price, 'currency': currency,
                            'rating': info.get('rating') or 0,
                            'stars': parse_stars(info.get('stars')),
                            'image_url': find_photo(info) or find_photo(extra.get(hotel_id))})
    return results, bool(payload.get('sandbox'))


