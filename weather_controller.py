import json

import requests
from flask import jsonify

from dto.CityTemperatureInfoDto import CityTemperatureInfoDto
from dto.ItemTemperatureInfoDto import ItemTemperatureInfoDto

API_KEY = "FdVaEZmQ6ijglygUyC9eKHKAVXr1ZaI3"

def get_location_key(city_name):
    base_url = "http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {
        "apikey": API_KEY,
        "q": city_name
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]["Key"], data[0]["GeoPosition"]["Latitude"], data[0]["GeoPosition"]["Longitude"]
    else:
        return "Ошибка при получении location_key:" + response.text, 400
    return None
def get_location_key_lat_lon(lat, lon):
    location_url = f"http://dataservice.accuweather.com/locations/v1/cities/geoposition/search?apikey={API_KEY}&q={lat},{lon}"

    response = requests.get(location_url)
    if response.status_code == 200:
        location_data = response.json()
        location_key = location_data['Key']
        return location_key
    else:
        return f"{response.status_code}", 400
def get_weather_info_lat_lon(lat, lon):
    try:
        location_key = get_location_key_lat_lon(lat, lon)
        if len(location_key) == 2:
            return f"Ошибка получения Location Key: {location_key[0]}", 400

        weather_url = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}?apikey={API_KEY}&details=true"

        response_weather = requests.get(weather_url)
        if response_weather.status_code == 200:
            weather_data = response_weather.json()
            return CityTemperatureInfoDto(weather_data[0]['Temperature']['Metric']['Value'],
                                          weather_data[0]['RelativeHumidity'],
                                          weather_data[0]['Wind']['Speed']['Metric']['Value'],
                                          weather_data[0]['PrecipitationSummary']['Precipitation']['Metric']['Value'])
        else:
            return f"Ошибка получения данных о погоде: {response_weather.json()['Message']}", 400
    except:
        return f'Точка не найдена', 400
def get_weaher_info(city_name):
    try:
        location_key = get_location_key(city_name)
        if location_key is None:
            return "Не смогли найти один из указанных городов", 400
        if len(location_key) == 2 :
            return f"Ошибка получения Location Key: {location_key[0]}", 400

        weather_url = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}?apikey={API_KEY}&details=true"

        response_weather = requests.get(weather_url)
        if response_weather.status_code == 200:
            weather_data = response_weather.json()
            return CityTemperatureInfoDto(weather_data[0]['Temperature']['Metric']['Value'],
                                   weather_data[0]['RelativeHumidity'],
                                   weather_data[0]['Wind']['Speed']['Metric']['Value'],
                                   weather_data[0]['PrecipitationSummary']['Precipitation']['Metric']['Value'])
        else:
            return f"Ошибка получения данных о погоде: {response_weather.json()['Message']}", 400
    except:
        return f'Город "{city_name}" не найден', 400



def get_weather_info_for_5_days(city_name=None, get_dict=True, lat=0, lon=0):
    if city_name is not None:
        location_key = get_location_key(city_name)
    else:
        location_key = get_location_key_lat_lon(lat, lon)
    if location_key is None:
        return "Не смогли найти указанный город: "+city_name, 400
    if len(location_key) == 2:
        return f"Ошибка получения Location Key: {location_key[0]}", 400
    base_url = f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key[0]}"
    lat = location_key[1]
    lon = location_key[2]
    params = {
        "apikey": API_KEY,
        "metric": "true",  # Для получения температуры в Цельсиях
        "details": "true"
    }
    response = requests.get(base_url, params=params)

    result = []
    if response.status_code == 200:
        forecast_data = response.json()
        for day in forecast_data["DailyForecasts"]:
            date = day["Date"]
            min_temp = day["Temperature"]["Minimum"]["Value"]
            max_temp = day["Temperature"]["Maximum"]["Value"]

            result.append(ItemTemperatureInfoDto((min_temp+ max_temp)/2,
                                                 day['Day']['RelativeHumidity']['Average'],
                                                 day['Day']['Wind']['Speed']['Value'],
                                                 day['Day']['PrecipitationProbability'],
                                                 date,
                                                 lat,
                                                 lon))
            if get_dict:
                result[-1] = result[-1].get_dict()
        return result
    else:
        return "Ошибка при получении прогноза погоды: " + response.text, 400