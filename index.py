import math

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import dash_leaflet as dl

import weather_controller

app = dash.Dash(__name__, prevent_initial_callbacks='initial_duplicate')

app.layout = html.Div([
    html.H1("Прогноз погоды"),

    html.H2("Выберите временной интервал прогноза:"),
    dcc.RadioItems(
        id="forecast-interval",
        options=[
            {"label": "Прогноз на 3 дня", "value": 3},
            {"label": "Прогноз на 5 дней", "value": 5},
        ],
        value=3,
        inline=True
    ),
    html.H2("Выберите что отображать на графике"),
    dcc.Dropdown(
        id="weather-parameter",
        options=[
            {"label": "Температура", "value": "temp"},
            {"label": "Влажность", "value": "humidity"},
            {"label": "Скорость ветра", "value": "wind_speed"},
            {"label": "Вероятность осадков", "value": "rain_chance"}
        ],
        value="temp",
        clearable=False
    ),
    html.H2("Введите точки маршрута"),

    html.Label("Введите начальную точку:"),
    html.Br(),
    dcc.Input(id="start-location", type="text", placeholder="Начальный город"),
    html.Br(),
    html.Label("Введите конечную точку:"),
    html.Br(),
    dcc.Input(id="end-location", type="text", placeholder="Конечный город"),
    html.Br(),
    html.Label("Промежуточные точки маршрута:"),
    html.Br(),
    dcc.Input(id="waypoint-input", type="text", placeholder="Промежуточный город"),
    html.Button("Добавить точку", id="add-waypoint", n_clicks=0),
    html.Br(),
    html.Div(id="waypoints-container"),
    html.Br(),

    html.Button("Получить прогноз", id="get-forecast", n_clicks=0),
    html.Br(),
    html.Div(id="weather-output"),
    html.Br(),
    dl.Map(
        id="route-map",
        center=[56, 37],
        zoom=5,
        children=[dl.TileLayer()],
        style={'width': '100%', 'height': '400px'}
    ),
])

@app.callback(
    Output("weather-output", "children", allow_duplicate=True),
    [Input("weather-parameter", "value")],
    [State("forecast-interval", "value"),
     State("start-location", "value"),
     State("end-location", "value"),
     State("waypoints-container", "children")
     ]
)
def update_graph(selected_param, interval, start_location, end_location, waypoints_container):
    return draw_graph(selected_param, interval, waypoints_container, start_location, end_location)[0]

@app.callback(
    Output("waypoints-container", "children"),
    [Input("add-waypoint", "n_clicks")],
    [State("waypoints-container", "children"),
     State("waypoint-input", "value")]
)
def update_waypoints(n_clicks, waypoints, new_waypoint):
    if new_waypoint:
        waypoints = waypoints or []
        waypoints.append(html.Div(f"Промежуточная точка: {new_waypoint}"))
    return waypoints

def get_countries(children, start_country, end_country):
    route_locations = [start_country]
    if children:
        for waypoint in children:
            route_locations.append(str(waypoint).split(':')[3].split("'")[0].strip())
    route_locations.append(end_country)
    return route_locations
@app.callback(
    Output("weather-output", "children"),
    Output("route-map", "children"),
    [Input("get-forecast", "n_clicks")],
    [State("forecast-interval", "value"),
     State("start-location", "value"),
     State("end-location", "value"),
     State("waypoints-container", "children"),
     Input("weather-parameter", "value")]
)
def display_forecast(n_clicks, interval, start, end, waypoints, param):

    if n_clicks > 0 and start and end:
        return draw_graph(param, interval, waypoints, start, end)
    return dash.no_update, dash.no_update

def draw_graph(param, interval, waypoints, start, end):
    if not(start) or not(end):
        return dash.no_update, dash.no_update
    figures = []
    markers = []
    configurate_graph = {}
    forecasts = []
    route_coords = []
    for city in get_countries(waypoints, start, end):
        city_forecast = weather_controller.get_weather_info_for_5_days(city, False)
        if len(city_forecast) == 2:
            return html.H1("Сервис не смог обработать ваш запрос. Возможно в названии города допущена ошибка или закончился токен\n"+city_forecast[0]), dash.no_update
        forecasts.append((city, city_forecast))
    for city, forecast_data in forecasts:
        configurate_graph[city] = forecast_data
    for city in configurate_graph.keys():
        dates = [day.date for day in configurate_graph[city]][:interval]
        temps = [day.temperature for day in configurate_graph[city]][:interval]
        wind_speeds = [day.speed_wind for day in configurate_graph[city]][:interval]
        rain_chances = [day.rain_percent for day in configurate_graph[city]][:interval]
        humidity = [day.humidity for day in configurate_graph[city]][:interval]

        lat = configurate_graph[city][0].lat
        lon = configurate_graph[city][0].lon
        forecast_summary = f"{city}: {math.ceil(sum(temps)/len(temps))}°C"
        route_coords.append((lat, lon))
        markers.append(dl.Marker(
            position=[lat, lon],
            children=[
                dl.Tooltip(city),
                dl.Popup(forecast_summary)
            ]
        ))
        if param == "temp":
            y_data = temps
            title = "Температура (°C)"
        elif param == "humidity":
            y_data = humidity
            title = "Влажность (%)"
        elif param == "wind_speed":
            y_data = wind_speeds
            title = "Скорость ветра (км/ч)"
        else:
            y_data = rain_chances
            title = "Вероятность осадков (%)"
        figures.append(html.H3(f"Прогноз для {city}"))
        figures.append(dcc.Graph(
            figure={
                "data": [
                    go.Scatter(x=dates, y=y_data, mode="lines+markers")
                ],
                "layout": go.Layout(
                    title=f"Прогноз погоды на {interval} дней",
                    xaxis={"title": "Дата"},
                    yaxis={"title": title}
                )
            }
        ))
    polyline = dl.Polyline(positions=route_coords, color="blue", weight=4)
    return figures, [dl.TileLayer(), dl.LayerGroup(markers), polyline]
if __name__ == "__main__":
    app.run_server(debug=True)