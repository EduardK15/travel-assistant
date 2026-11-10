from datetime import date, timedelta, datetime
from uuid import uuid4
from threading import Lock

import requests
from flask import Flask, request, render_template, redirect, url_for
from openai import APITimeoutError, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError
from ai_service import interpret
from hotel_service import fetch_catalog, fetch_rates

app = Flask(__name__)
RESULTS = {}
RESULTS_LOCK = Lock()
RESULT_TTL_SECONDS = 1800


def page(**kwargs):
    defaults = dict(query='', checkin=(date.today()+timedelta(days=14)).isoformat(),
                    checkout=(date.today()+timedelta(days=16)).isoformat(), adults=2,
                    error=None, searched=False, hotels=[], city='', sandbox=False,
                    max_price='', sort_by='price', min_stars=0, nights=1, sort_note='')
    defaults.update(kwargs)
    return render_template('index.html', **defaults)


@app.route('/')
def home():
    return page()


@app.route('/results/<result_id>')
def show_results(result_id):
    with RESULTS_LOCK:
        item = RESULTS.get(result_id)
    if not item or datetime.now().timestamp() - item['created'] > RESULT_TTL_SECONDS:
        return page(error='Результаты устарели. Выполните поиск ещё раз.'), 404
    return page(**item['context'])


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        return page()
    query = request.form.get('query', '').strip()
    checkin = request.form.get('checkin', '')
    checkout = request.form.get('checkout', '')
    try:
        adults = int(request.form.get('adults', '2'))
    except ValueError:
        adults = 0
    max_price_text = request.form.get('max_price', '').strip()
    sort_by = request.form.get('sort_by', 'price')
    try:
        min_stars = int(request.form.get('min_stars', '0'))
    except ValueError:
        min_stars = -1
    context = dict(query=query, checkin=checkin, checkout=checkout, adults=adults,
                   max_price=max_price_text, sort_by=sort_by, min_stars=min_stars)
    try:
        if not query:
            raise ValueError('Введите запрос.')
        start, end = date.fromisoformat(checkin), date.fromisoformat(checkout)
        if start < date.today() or end <= start or (end-start).days > 30:
            raise ValueError('Проверьте даты: выезд после заезда, не более 30 ночей.')
        if not 1 <= adults <= 6:
            raise ValueError('Укажите от 1 до 6 взрослых.')
        params = interpret(query)
        city = params['city'].strip()
        limit = params['limit']
        if not city:
            raise ValueError('Укажите город.')
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError('Количество гостиниц должно быть от 1 до 20.')
        if min_stars not in (0, 3, 4, 5):
            raise ValueError('Неверная категория гостиницы.')
        if sort_by not in ('price', 'rating'):
            raise ValueError('Неверный вариант сортировки.')
        budget = None
        if max_price_text:
            try:
                budget = int(max_price_text)
            except ValueError:
                raise ValueError('Максимальная стоимость должна быть целым числом.')
            if budget <= 0:
                raise ValueError('Укажите бюджет больше 0 ₪ или оставьте поле пустым.')
        catalog = fetch_catalog(city)
        if catalog:
            hotels, sandbox = fetch_rates(catalog, checkin, checkout, adults)
        else:
            hotels, sandbox = [], False
        if min_stars:
            hotels = [h for h in hotels if h['stars'] is not None and h['stars'] >= min_stars]
        # Сравниваем суммы только в ILS, без выдуманного курса конвертации.
        if budget is not None:
            hotels = [h for h in hotels if h['currency'] == 'ILS' and h['price'] <= budget]
        # Оценки гостей в текущем ответе не проверены; сортируем по цене.
        hotels.sort(key=lambda h: (h['currency'] != 'ILS', h['price']))
        photo_count = sum(bool(h.get('image_url')) for h in hotels[:limit])
        app.logger.warning('Hotel images found in API response: %s of %s', photo_count, min(len(hotels), limit))
        sort_note = ('Nuitee пока не предоставил подтверждённые оценки гостей. '
                     'Результаты отсортированы по цене.' if sort_by == 'rating' else '')
        result_context = dict(**context, searched=True, city=city, hotels=hotels[:limit],
                              sandbox=sandbox, sort_note=sort_note, nights=(end-start).days)
        result_id = uuid4().hex
        with RESULTS_LOCK:
            now = datetime.now().timestamp()
            expired = [key for key, item in RESULTS.items()
                       if now - item['created'] > RESULT_TTL_SECONDS]
            for key in expired:
                RESULTS.pop(key, None)
            RESULTS[result_id] = {'created': now, 'context': result_context}
        # Post/Redirect/Get: refreshing results won't resubmit the search.
        return redirect(url_for('show_results', result_id=result_id), code=303)
    except ValueError as exc:
        return page(**context, error=str(exc)), 400
    except APITimeoutError:
        return page(**context, error='OpenAI слишком долго отвечает. Попробуйте ещё раз.'), 504
    except APIConnectionError:
        return page(**context, error='Не удалось связаться с OpenAI. Проверьте интернет и повторите попытку.'), 502
    except RateLimitError:
        return page(**context, error='Достигнут лимит запросов OpenAI. Попробуйте позже.'), 429
    except AuthenticationError:
        return page(**context, error='Ошибка авторизации OpenAI. Проверьте API-ключ.'), 502
    except APIStatusError:
        return page(**context, error='Сервис OpenAI временно не смог обработать запрос.'), 502
    except requests.exceptions.Timeout:
        return page(**context, error='Nuitee не ответил вовремя. Попробуйте позже.'), 504
    except requests.exceptions.ConnectionError:
        return page(**context, error='Не удалось соединиться с Nuitee. Проверьте интернет и повторите попытку.'), 502
    except requests.exceptions.RequestException:
        return page(**context, error='Ошибка соединения с Nuitee. Попробуйте позже.'), 502
    except Exception:
        app.logger.error('Search failed unexpectedly (details and credentials omitted)')
        return page(**context, error='Не удалось выполнить поиск. Попробуйте позже.'), 502


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
