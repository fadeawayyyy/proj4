class ItemTemperatureInfoDto:
    def __init__(self, temperature, vlaznost, speed_veter, maybe_rain, date, lat, lon):
        self.temperature = temperature
        self.humidity = vlaznost
        self.speed_wind = speed_veter
        self.rain_percent = maybe_rain
        self.date = date
        self.lat = lat
        self.lon = lon

    def it_bad_weather(self, temperature, speed_windy, rain_percent):
        if temperature < -15:
            return True
        if temperature > 30:
            return True
        if speed_windy > 20:
            return True
        if rain_percent > 85:
            return True

        return False
    def get_dict(self):
        return {
            'temperature': self.temperature,
            'humidity': str(self.humidity)+"%",
            'speed_wind': str(self.speed_wind)+"km/h",
            'rain_percent': str(self.rain_percent)+"%",
            'it_bad_weather': self.it_bad_weather(self.temperature, self.speed_wind, self.rain_percent),
            'lat': self.lat,
            'lon': self.lon,
            'date': self.date
        }