from flask import Flask, jsonify, request, render_template

import weather_controller

app = Flask(__name__)
API_KEY = "rG5GGCfrFggkWmGmA355CHIjRPyLeVUE"

@app.route('/weather/get/{city}', methods=['GET'])
def weather_get(city):
    weather_info = weather_controller.get_weaher_info(city)

    if type(weather_info) == tuple:
        return weather_info
    return jsonify(weather_info.get_dict()), 200

@app.route('/weather/get/{lat}/{lon}', methods=['GET'])
def weather_get_from_location(lat, lon):
    weather_info = weather_controller.get_weather_info_lat_lon(lat, lon)

    if type(weather_info) == tuple:
        return weather_info
    return jsonify(weather_info.get_dict()), 200

@app.route('/weather/get/5days', methods=['GET'])
def weather_get_week():
    city = request.args.get('city')
    if city is not None:
        weather_info = weather_controller.get_weather_info_for_5_days(city)
    else:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        weather_info = weather_controller.get_weather_info_for_5_days(lat=lat, lon=lon)
    if type(weather_info) == tuple:
        return weather_info
    return jsonify(weather_info), 200
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)