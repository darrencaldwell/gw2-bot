import requests
import typing as t
import datetime
import random
import pandas
import config as cf
import asyncio

dublin_url = "http://api.openweathermap.org/data/2.5/forecast?lat=53.35&lon=-6.266&appid="+ cf.WEATHER_API_KEY

async def get_weather_with_key(lat: str, long: str):
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={long}&appid="+ cf.WEATHER_API_KEY
    return requests.get(url).json()

try:
    dataframe = pandas.read_csv(cf.WEATHER_REQUEST_FILENAME, index_col=0)
except pandas.errors.EmptyDataError:
    dataframe = pandas.DataFrame(columns=["lat", "long"])

weather_csv_lock = asyncio.Lock()

async def add_user_to_dataframe(username: str, lat: float, long: float) -> None | str:
    username = str(username)
    async with weather_csv_lock:
        if username in dataframe.index:
            return "User already listed"
        
        if not (-90 < lat < 90) or not (-180 < long < 180):
            return "Longitude invalid" 
        
        dataframe.loc[username] = pandas.Series({"lat": lat, "long": long})
        dataframe.to_csv(cf.WEATHER_REQUEST_FILENAME)

        return None

async def remove_user_from_dataframe(username: str) -> None | str:
    username = str(username)
    async with weather_csv_lock:
        if username not in dataframe.index:
            return "User not present to be deleted"
        
        if username == cf.UNBANNABLE_ID:
            return "Nice try Darren"

        dataframe.drop(username, axis=0, inplace=True)
        dataframe.to_csv(cf.WEATHER_REQUEST_FILENAME)

#foo = asyncio.run(get_users_from_dataframe())
async def parse_weather(row) -> t.List[int]:
    lat = row["lat"]
    long = row["long"]
    forecast = await get_weather_with_key(lat, long)
    forecast: t.List[t.Dict[str, t.Any]] = forecast["list"]
    
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

async def get_users_from_dataframe() -> t.Dict[str, t.List[int]]:
    async with weather_csv_lock:
        iteritems = iter(dataframe)
        next(iteritems)

        return {name: await parse_weather(row) for name, row in dataframe.iterrows()}
                
def get_times(rain_times):
    times = []

    rt_iter = iter(rain_times)

    start_time = next(rt_iter)

    last_time = start_time

    for time in rt_iter:
        if time > last_time + cf.WEATHER_TOLERANCE:
            times.append((start_time, min(last_time+cf.WEATHER_TOLERANCE, 24)))
            start_time = time

        last_time = time
    
    times.append((start_time, min(last_time + cf.WEATHER_TOLERANCE, 24)))

    return times

def generate_time_line(tup: t.Tuple[int, int]):
    return "\n- between " + str(tup[0]) + " and " + str(tup[1]) + " o'clock!"

def generate_message(times):
    if not times:
        return None
    
    times = get_times(times)

    with open("whimsey.txt", "r") as f:
        lines = [txt[:-1] for txt in f]
    
    message = "{greeting} {will_rain} {times_are}"  #+ random.choice(lines)

    for line in times:
        message += generate_time_line(line)

    return message

async def generate_messages():
    user_time_dict = await get_users_from_dataframe()

    return {i: generate_message(v) for i, v in user_time_dict.items() if v}
