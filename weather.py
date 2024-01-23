from config import WEATHER_API_KEY
import requests
import typing as t
import datetime
import random

dublin_url = "http://api.openweathermap.org/data/2.5/forecast?lat=53.35&lon=-6.266&appid="+ WEATHER_API_KEY

def get_weather_with_key():
    return requests.get(dublin_url).json()


def parse_weather() -> t.List[int]:
    forecast: t.List[t.Dict[str, t.Any]] = get_weather_with_key()["list"]
    rain_times = []

    for prediction in forecast:
        pred_date, pred_time = prediction["dt_txt"].split(" ")
        _, month, day = pred_date.split("-")
        
        current_date = datetime.datetime.now()

        if int(month) == current_date.month and int(day) == current_date.day:
            weather_list = prediction["weather"]

            if any(weather["main"] == "Rain" for weather in weather_list):
                hour, _, _ = pred_time.split(":")
                rain_times.append(int(hour))
    
    return rain_times
                
def get_times(rain_times = None):
    if not rain_times:
        rain_times = parse_weather()

    times = []

    rt_iter = iter(rain_times)

    start_time = next(rt_iter)

    last_time = start_time

    for time in rt_iter:
        if time > last_time + 3:
            times.append((start_time, min(last_time+3, 24)))
            start_time = time

        last_time = time
    
    times.append((start_time, min(last_time + 3, 24)))

    return times

def generate_time_line(tup: t.Tuple[int, int]):
    return "- between " + str(tup[0]) + " and " + str(tup[1]) + " o'clock!\n"

def generate_message():
    times = get_times()

    if not times:
        return None
    
    with open("whimsey.txt", "r") as f:
        lines = [txt[:-1] for txt in f]
    
    message = random.choice(lines)

    with open("ending.txt", "r") as f:
        lines = [txt for txt in f]

    ending = random.choice(lines)

    message += " Looks like it's going to rain! Better be careful with that washing! "

    message += ending

    for line in times:
        message += generate_time_line(line)

    return message



