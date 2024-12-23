import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
    CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

from TelegramBot import weather_client

API_TOKEN = '8047001033:AAFnHiCQHUxdgYNjr6gZp2UkkqRy1MlP1pY'
WEATHER_API_TOKEN = 'iupI2OZQOCrGIKATVaSPwcTHCAdX1Cf7'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

dp.include_router(router)


class RouteStates(StatesGroup):
    start_city = State()
    end_city = State()
    intermediate_cities = State()  # New state for intermediate cities


@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "Привет! Я бот для прогноза погоды. "
        "Отправь /weather, чтобы получить прогноз для маршрута, или /help для справки."
    )


@router.message(Command("help"))
async def send_help(message: Message):
    await message.answer(
        "/weather - Получить прогноз погоды\n"
        "Введите начальную и конечную точки маршрута и выберите временной интервал прогноза (например, 3 дня или 5 дней)."
    )


@router.message(Command("weather"))
async def weather_command(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отправить местоположение", request_location=True)]])
    await message.answer("Введите начальный город для маршрута или отправьте своё местоположение:",
                         reply_markup=keyboard)
    await state.set_state(RouteStates.start_city)


@router.message(RouteStates.start_city)
async def process_start_city(message: Message, state: FSMContext):
    if message.location is not None:
        await state.update_data(start_city=f"GPS:{message.location.latitude},{message.location.longitude}")
    else:
        await state.update_data(start_city=message.text)

    await message.answer("Теперь введите конечный город:")
    await state.set_state(RouteStates.end_city)


@router.message(RouteStates.end_city)
async def process_end_city(message: Message, state: FSMContext):
    if message.location is not None:
        await state.update_data(end_city=f"GPS:{message.location.latitude},{message.location.longitude}")
    else:
        await state.update_data(end_city=message.text)

    # Ask for intermediate cities with a "Done" button option
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text="Готово")]])
    await message.answer("Введите промежуточные города через запятую (или нажмите 'Готово', если нет):",
                         reply_markup=keyboard)

    await state.set_state(RouteStates.intermediate_cities)


@router.message(RouteStates.intermediate_cities)
async def process_intermediate_cities(message: Message, state: FSMContext):
    if message.text.strip().lower() == 'готово':
        # User is done with inputting intermediate cities
        await message.answer("Выберите временной интервал прогноза:", reply_markup=create_interval_keyboard())
        return

    intermediate_cities = message.text.strip()

    # Store intermediate cities in the state
    await state.update_data(intermediate_cities=intermediate_cities.split(','))

    # Proceed to choose forecast interval
    await message.answer("Выберите временной интервал прогноза:", reply_markup=create_interval_keyboard())


def create_interval_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Прогноз на 3 дня", callback_data="interval_3"),
        InlineKeyboardButton(text="Прогноз на 5 дней", callback_data="interval_5")
    ]])
    return keyboard


def map_forecast_to_str(forecast, interval):
    result = ''
    for i in range(interval):
        day = forecast[i]
        result += (f'День {i + 1}\n'
                   f'Температура: {round(day["temperature"], 2)}°C\n'
                   f'Вероятность осадков: {day["rain_percent"]}%\n'
                   f'Влажность: {day["humidity"]}%\n\n')
    return result


@router.callback_query()
async def interval_chosen(callback_query: CallbackQuery, state: FSMContext):
    interval = int(callback_query.data.split("_")[1])
    data = await state.get_data()

    start_city = data["start_city"]
    end_city = data["end_city"]

    # Get intermediate cities if they exist
    intermediate_cities = data.get("intermediate_cities", [])

    # Collect forecasts for all cities
    forecasts = {}

    # Start city forecast
    if 'GPS' in start_city:
        forecasts['start'] = weather_client.get_weather_from_location(start_city.split(':')[1].split(',')[0],
                                                                      start_city.split(':')[1].split(',')[1])
    else:
        forecasts['start'] = weather_client.get_weather_from_city_name(start_city)

    # End city forecast
    if 'GPS' in end_city:
        forecasts['end'] = weather_client.get_weather_from_location(end_city.split(':')[1].split(',')[0],
                                                                    end_city.split(':')[1].split(',')[1])
    else:
        forecasts['end'] = weather_client.get_weather_from_city_name(end_city)

    # Intermediate city forecasts
    forecasts['intermediate'] = []

    for city in intermediate_cities:
        city_forecast = weather_client.get_weather_from_city_name(city.strip())
        forecasts['intermediate'].append(city_forecast)

    # Handle responses and check for errors
    if isinstance(forecasts['start'], str) and "Неверный API ключ." in forecasts['start']:
        await callback_query.message.answer("Ошибка: Неверный API ключ для начального города.")
        return

    if isinstance(forecasts['end'], str) and "Неверный API ключ." in forecasts['end']:
        await callback_query.message.answer("Ошибка: Неверный API ключ для конечного города.")
        return

    for city_forecast in forecasts['intermediate']:
        if isinstance(city_forecast, str) and "Неверный API ключ." in city_forecast:
            await callback_query.message.answer(f"Ошибка: Неверный API ключ для промежуточного города.")
            return

    # Process forecasts if no errors occurred
    start_forecast_str = map_forecast_to_str(forecasts['start'], interval)
    end_forecast_str = map_forecast_to_str(forecasts['end'], interval)

    intermediate_forecasts_strs = [map_forecast_to_str(forecast, interval) for forecast in forecasts['intermediate']]

    # Formatting the output message with intermediate points included
    if interval == 3 and len(intermediate_forecasts_strs) == 0:
        message_text = (
                f"*Прогноз для маршрута на {interval} дня:*\n\n"
                f"*Начальная точка: {start_city}*\n"
                f"{start_forecast_str}\n"
                f"*Конечная точка: {end_city}*\n"
                f"{end_forecast_str}\n"
        )
    elif interval == 5 and len(intermediate_forecasts_strs) == 0:
        message_text = (
                f"*Прогноз для маршрута на {interval} дней:*\n\n"
                f"*Начальная точка: {start_city}*\n"
                f"{start_forecast_str}\n"
                f"*Конечная точка: {end_city}*\n"
                f"{end_forecast_str}\n"
        )
    elif interval == 3 and len(intermediate_forecasts_strs) != 0:
        message_text = (
            f"*Прогноз для маршрута на {interval} дня:*\n\n"
            f"*Начальная точка: {start_city}*\n"
            f"{start_forecast_str}\n"
            f"*Конечная точка: {end_city}*\n"
            f"{end_forecast_str}\n"
            f"*Промежуточные точки:* \n"
           + "\n".join(
               [f"*{city_name}:*\n{forecast}" for (city_name, forecast) in zip(intermediate_cities, intermediate_forecasts_strs)]
           )
   )
    else:
        message_text = (
                f"*Прогноз для маршрута на {interval} дней:*\n\n"
                f"*Начальная точка: {start_city}*\n"
                f"{start_forecast_str}\n"
                f"*Конечная точка: {end_city}*\n"
                f"{end_forecast_str}\n"
                f"*Промежуточные точки:* \n"
           + "\n".join(
               [f"*{city_name}:*\n{forecast}" for (city_name, forecast) in zip(intermediate_cities, intermediate_forecasts_strs)]
           )
   )

    await callback_query.message.answer(message_text, parse_mode='Markdown')


if __name__ == '__main__':
    dp.run_polling(bot, skip_updates=True)
