import json
from config import client

def interpret(query):
    answer = client.responses.create(
        model='gpt-4.1-mini',
        instructions=('Extract search parameters from Russian or English hotel request. '
                      'City must be in English, e.g. Tel Aviv, Haifa, Eilat, Jerusalem. '
                      'Return empty city if unspecified. Default limit 5. '
                      'Sort by rating only if user explicitly requests highest rated; otherwise price. '
                      'Do not invent prices or hotels.'),
        input=query,
        text={'format': {'type': 'json_schema', 'name': 'hotel_query', 'strict': True,
            'schema': {'type': 'object', 'properties': {
                'city': {'type': 'string'}, 'limit': {'type': 'integer'},
                'sort_by': {'type': 'string', 'enum': ['price', 'rating']}},
                'required': ['city', 'limit', 'sort_by'], 'additionalProperties': False}}})
    return json.loads(answer.output_text)


