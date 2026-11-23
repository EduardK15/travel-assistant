import os
from getpass import getpass
from openai import OpenAI

def secret(name, prompt):
    value = os.getenv(name) or getpass(prompt)
    value = value.replace('\x00', '').strip()
    if not value:
        raise ValueError(f'Не задан {name}')
    return value


client = OpenAI(api_key=secret('OPENAI_API_KEY', 'Введите OpenAI API-ключ: '),
                timeout=15.0, max_retries=1)
NUITEE_KEY = secret('NUITEE_API_KEY', 'Введите Nuitee API-ключ: ')
HEADERS = {'X-API-Key': NUITEE_KEY, 'Accept': 'application/json'}
BASE = 'https://api.liteapi.travel/v3.0'

