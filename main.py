from flask import Flask, jsonify, request, render_template
import requests
import logging
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

app = Flask(__name__)
my_api_key = 'iupI2OZQOCrGIKATVaSPwcTHCAdX1Cf7'  # Ваш API ключ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_location_key_by_city(city, API_KEY=my_api_key):
    params = {"apikey": API_KEY, "q": city}
    try:
        response = requests.get("http://dataservice.accuweather.com/locations/v1/cities/search", params=params,
                                timeout=5)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0].get("Key")
        else:
            return None
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 503:
            logger.error("Неверный API ключ или превышен лимит запросов")
            raise ValueError("Неверный API ключ или превышен лимит запросов")
        logger.error(f"HTTP error при запросе locationKey для города {city}: {http_err}")
        return "Ошибка при запросе данных."
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Ошибка соединения при запросе locationKey для города {city}: {conn_err}")
        return "Ошибка соединения. Проверьте интернет-соединение."
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Тайм-аут при запросе locationKey для города {city}: {timeout_err}")
        return "Тайм-аут запроса. Попробуйте позже."
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Произошла ошибка при запросе locationKey для города {city}: {req_err}")
        return "Произошла ошибка запроса."


def check_bad_weather(temperature, wind_speed, rain_probability):
    '''Моя субъективная оценка плохих погодных условий'''
    if temperature < -15 or temperature > 35:
        return "Плохие погодные условия"
    if wind_speed > 50:
        return "Плохие погодные условия"
    if rain_probability > 60:
        return "Плохие погодные условия"
    return "Хорошие погодные условия"


def get_weather(location_key, API_KEY=my_api_key):
    url = f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}"
    params = {"apikey": API_KEY, "details": "true", "metric": "true"}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        forecast = data.get("DailyForecasts", [])[0]

        weather_data = {
            "temperature": forecast["Temperature"]["Maximum"]["Value"],
            "humidity": forecast["Day"]["RelativeHumidity"]["Average"],
            "wind_speed": forecast["Day"]["Wind"]["Speed"]["Value"],
            "rain_probability": forecast["Day"]["RainProbability"],
        }

        # Оценка погодных условий
        weather_condition = check_bad_weather(
            weather_data["temperature"],
            weather_data["wind_speed"],
            weather_data["rain_probability"],
        )

        weather_data["weather_condition"] = weather_condition
        return weather_data
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 503:
            logger.error("Неверный API ключ или превышен лимит запросов")
            raise ValueError("Неверный API ключ или превышен лимит запросов")
        logger.error(f"HTTP error при запросе погоды для locationKey {location_key}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Ошибка соединения при запросе погоды для locationKey {location_key}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Тайм-аут при запросе погоды для locationKey {location_key}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Произошла ошибка при запросе погоды для locationKey {location_key}: {req_err}")

    return None


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    if request.method == "POST":
        start_city = request.form.get("start_city")
        end_city = request.form.get("end_city")

        if start_city and end_city:
            try:
                start_location_key = get_location_key_by_city(start_city)
                end_location_key = get_location_key_by_city(end_city)

                if not start_location_key and not end_location_key:
                    weather = {"error": "Оба города не найдены. Проверьте правильность введённых названий."}
                elif not start_location_key:
                    weather = {"error": f'Начальная точка "{start_city}" не найдена. Проверьте правильность названия.'}
                elif not end_location_key:
                    weather = {"error": f'Конечная точка "{end_city}" не найдена. Проверьте правильность названия.'}
                else:
                    start_weather = get_weather(start_location_key)
                    end_weather = get_weather(end_location_key)
                    if start_weather == "Неверный API ключ." or end_weather == "Неверный API ключ.":
                        weather = {"error": "Неверный API ключ. Проверьте настройки."}
                    if start_weather and end_weather:
                        weather = {
                            "start_temperature": start_weather["temperature"],
                            "start_humidity": start_weather["humidity"],
                            "start_wind_speed": start_weather["wind_speed"],
                            "start_rain_probability": start_weather["rain_probability"],
                            "start_weather_condition": start_weather["weather_condition"],
                            "end_temperature": end_weather["temperature"],
                            "end_humidity": end_weather["humidity"],
                            "end_wind_speed": end_weather["wind_speed"],
                            "end_rain_probability": end_weather["rain_probability"],
                            "end_weather_condition": end_weather["weather_condition"],
                        }
                    else:
                        weather = {"error": "Не удалось получить данные о погоде для одного из городов."}

            except ValueError as ve:
                weather = {"error": str(ve)}

            except Exception as e:
                logger.error(f"Ошибка при обработке запроса: {e}")
                weather = {"error": "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."}

    return render_template("index.html", weather=weather)


# Создание приложения Dash
dash_app = Dash(__name__, server=app, url_base_pathname='/dash/')


@dash_app.callback(
    Output('weather-graphs', 'children'),
    [Input('start-city', 'value'), Input('end-city', 'value')]
)
def update_graph(start_city, end_city):
    if start_city and end_city:
        start_location_key = get_location_key_by_city(start_city)
        end_location_key = get_location_key_by_city(end_city)

        if start_location_key and end_location_key:
            start_weather = get_weather(start_location_key)
            end_weather = get_weather(end_location_key)

            if start_weather and end_weather:
                graphs = []

                # График температуры
                temp_graph = dcc.Graph(
                    figure={
                        'data': [
                            go.Bar(x=[start_city], y=[start_weather['temperature']], name=start_city),
                            go.Bar(x=[end_city], y=[end_weather['temperature']], name=end_city)
                        ],
                        'layout': {
                            'title': 'Сравнение температуры (°C)',
                            'yaxis': {'title': 'Температура (°C)'}
                        }
                    }
                )
                graphs.append(temp_graph)

                # График влажности
                humidity_graph = dcc.Graph(
                    figure={
                        'data': [
                            go.Bar(x=[start_city], y=[start_weather['humidity']], name=start_city),
                            go.Bar(x=[end_city], y=[end_weather['humidity']], name=end_city)
                        ],
                        'layout': {
                            'title': 'Сравнение влажности (%)',
                            'yaxis': {'title': 'Влажность (%)'}
                        }
                    }
                )
                graphs.append(humidity_graph)

                # График скорости ветра
                wind_graph = dcc.Graph(
                    figure={
                        'data': [
                            go.Bar(x=[start_city], y=[start_weather['wind_speed']], name=start_city),
                            go.Bar(x=[end_city], y=[end_weather['wind_speed']], name=end_city)
                        ],
                        'layout': {
                            'title': 'Сравнение скорости ветра (км/ч)',
                            'yaxis': {'title': 'Скорость ветра (км/ч)'}
                        }
                    }
                )
                graphs.append(wind_graph)

                # График вероятности дождя
                rain_graph = dcc.Graph(
                    figure={
                        'data': [
                            go.Bar(x=[start_city], y=[start_weather['rain_probability']], name=start_city),
                            go.Bar(x=[end_city], y=[end_weather['rain_probability']], name=end_city)
                        ],
                        'layout': {
                            'title': 'Сравнение вероятности дождя (%)',
                            'yaxis': {'title': 'Вероятность дождя (%)'}
                        }
                    }
                )
                graphs.append(rain_graph)

                return graphs

    return []


# Обновленный шаблон для Dash приложения
dash_app.layout = html.Div([
    html.H1('Сравнение погодных условий', style={'textAlign': 'center'}),
    html.Div([
        dcc.Input(
            id='start-city',
            type='text',
            placeholder='Введите название города, например: Москва',
            style={'margin': '10px', 'padding': '5px'}
        ),
        dcc.Input(
            id='end-city',
            type='text',
            placeholder='Введите название города, например: Санкт-Петербург',
            style={'margin': '10px', 'padding': '5px'}
        ),
    ], style={'textAlign': 'center'}),
    html.Div(id='weather-graphs', style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center'})
])

if __name__ == "__main__":
    app.run(debug=True)
