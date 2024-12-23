import requests

API_URL = 'http://127.0.0.1:5000'

def get_weather_from_city_name(city_name):
    try:
        response = requests.get(f"{API_URL}/weather/get/5days?city={city_name}")
        if response.status_code != 200:
            return None
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 503:
            raise ValueError("Неверный API ключ или превышен лимит запросов")

def get_weather_from_location(lat, lon):
    response = requests.get(f"{API_URL}/weather/get/5days?lat={lat}&lon={lon}")
    if response.status_code != 200:
        return None
    json = response.json()
    return json