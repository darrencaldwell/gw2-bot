# every day at 9am create a post in specific channel
# apply certain emotes to the post
# create a thread with today's date
import asyncio
# https://discord.com/api/oauth2/authorize?client_id=1172277989103378454&permissions=34359740480&scope=bot

# bot.py
import os

import discord
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv
import datetime
import declarative_tree as dt
from sympy import Not
from cond_parser import parse_string
import config as cf
from typing import Dict
import pandas
from log import LogObject
import weather as wth
from drk import my_mut_record
import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TIME = datetime.time(hour=9),

# TESTING
#CHANNEL_ID = 1172277801165004926
#ROLE_ID = 1173352152568172685
#GUILD_ID = 1172277800493928582

# REAL
CHANNEL_ID = 1166772628216893620
ROLE_ID = 1168850068665794661
GUILD_ID = 1099793030678069338
WEATHER_CHANNEL_ID = 1199439405245550703

#OSCAR TESTING
# CHANNEL_ID = 723899751732346964
# ROLE_ID = 1180661716107931658
# GUILD_ID = 723899751732346960
# WEATHER_CHANNEL_ID = 723899751732346964

GUILD = discord.Object(id=GUILD_ID)

EMOJI_MAP = {
    "🍎": "1200 - 1400",
    "🫐": "1400 - 1600",
    "🍊": "1600 - 1800",
    "⛅": "1800 - 1900",
    "🌙": "1900 - 2000",
    "🌑": "2000 - 2100",
    "😴": "2100 - 2200",
    "3️⃣": "Tier 3 Fractals",
    "4️⃣": "Tier 4 Fractals",
    "🇨🇲": "Challenge Mode Fractal",
    "🚷": "Strike Mission",
    "🚫": "I'm unavailable",
}

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

adjust_prob_by = cf.DAILY_INVOCATIONS // 24

def seconds_until_9am() -> float:
    now = datetime.datetime.now()
    target = (now + datetime.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    diff = (target - now).total_seconds()
    print(f"{target} - {now} = {diff}")
    return diff

def parse_cond_line(line: Dict[str, str]) -> dt.Condition | None:
    try:
        cond = dt.Condition(condition = parse_string(line["condition"]), message = dt.Response(message = line["response"], author = line["author"]))
    except Exception as e:
        print("Failed to load line " + str(line) + " " + str(e))
        return None

    return cond

dataframe = pandas.read_csv(cf.RESPONSE_FILENAME)

async def write_dataframe_task():
    async with dataframe_lock:
        dataframe.to_csv(cf.RESPONSE_FILENAME)

def gen_tree_from_csv():
    condslist = [parsed_line for line in dataframe.iterrows() if (parsed_line := parse_cond_line(line[1]))]

    return dt.process_conds(condslist)

def get_messages_owned_by(username: str):
    return (i[1] for i in dataframe.iterrows() if i[1]["author"] == username)

with LogObject("tree building"):
    tree = gen_tree_from_csv()

message_lock = asyncio.Lock()
dataframe_lock = asyncio.Lock()

def build_message(role) -> str:
    intro = (f"{role.mention} Good morning members I hope you have a good "
             f"{WEEKDAYS[datetime.date.today().weekday()]}.\n"
             f"Please react to the relevant emotes for today's adventures!\n\n")

    reacts = ""
    for emoji in EMOJI_MAP.keys():
        reacts += f"{emoji} : {EMOJI_MAP.get(emoji)}\n"

    return intro + reacts

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        channel = self.get_channel(CHANNEL_ID)
        guild = self.get_guild(GUILD_ID)
        role = guild.get_role(ROLE_ID)
        other_channel = self.get_channel(WEATHER_CHANNEL_ID)

        cog = MyCog(self, channel, other_channel, role)
        print(f'Logged on as {self.user} for channel {channel}')

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)

    async def on_message(self, message):
        if message.author == client.user:
            return
        
        content = message.content.lower()
        channel = message.channel

        if message.author.id == 511552638853185536:
            if not my_mut_record.has_been_used:
                my_mut_record.has_been_used = True
                await channel.send(my_mut_record.message)

        async with message_lock: 
            # technically this is bad, ideally we'd use a read/write lock here
            # but python doesn't have one natively and adding another dependency for this seems not worth it

            messages = tree.get_messages(message)

        for response in messages:
            await channel.send(response)


class MyCog(commands.Cog):
    def __init__(self, client: discord.Client, channel, other_channel, role):
        self.client = client
        self.channel = channel
        self.other_channel = other_channel

        self.role = role
        self.my_task.start()
        self.adjust_probs.start()
        self.get_weather.start()

    def cog_unxload(self):
        self.my_task.cancel()
        self.adjust_probs.cancel()

    @tasks.loop(seconds=10)
    async def my_task(self):
        await asyncio.sleep(seconds_until_9am())
        date_string = f"{datetime.datetime.today().day}/{datetime.datetime.today().month}"
        print(f"Posting thread for {date_string}")
        message = await self.channel.send(build_message(self.role))
        thread = await message.create_thread(name=date_string, auto_archive_duration=1440)
        for react in EMOJI_MAP.keys():
            await message.add_reaction(react)

    @tasks.loop(hours=1)
    async def reset_mut_record(self):
        if datetime.datetime.now().hour == my_mut_record.reset_time:
            my_mut_record.has_been_used = False
    
    @tasks.loop(hours=1)
    async def adjust_probs(self):
        for author in dt.AUTHOR_DICT:
            dt.AUTHOR_DICT[author] = max(0, dt.AUTHOR_DICT[author] - adjust_prob_by)

    @tasks.loop(hours=1)
    async def pregenerate_graph(self):
        tree.get_graph()

    @tasks.loop(seconds=10)
    async def get_weather(self):
        await asyncio.sleep(seconds_until_9am()-1)
        messages = await wth.generate_messages()

        for user, message in messages.items():
            if message:
                try:
                    user = await self.client.fetch_user(user)
                except:
                    continue
                
                await self.other_channel.send(user.mention)
                await self.other_channel.send(message)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

client = MyClient(intents=intents)

with open("tutorial.md", "r") as f:
    tutorial_text =  f.read()

@client.tree.command()
async def new_response(interaction: discord.Interaction, response: str, condition: str):
    """Adds a new message, and a Boolean condition that causes it to be posted. Example: contains: \"foo\" & onein: 3"""
    global tree

    condition = condition.lower()

    try:
        parse_string(condition)
    
    except Exception as e:
        await interaction.response.send_message("Error: " + str(e) + " use /tutorialisland to learn how to message good", ephemeral=True)
        return

    await interaction.response.send_message("Condition parsed succesfully, just adding it to the tree :) ")

    async with dataframe_lock:
        dataframe.loc[len(dataframe)] = {"response": response, "condition": condition, "author": interaction.user.name}

        tree_obj = gen_tree_from_csv()

        dataframe.to_csv(cf.RESPONSE_FILENAME, index=False)

    async with message_lock:
        tree = tree_obj

@client.tree.command()
async def new_weather(interaction: discord.Interaction, lat: float, long: float):
    """Put in your lat and long to get weather pings"""
    ret_code = await wth.add_user_to_dataframe(interaction.user.id, lat, long)

    if ret_code:
        await interaction.response.send_message(ret_code, ephemeral=True)
    
    else:
        await interaction.response.send_message("Cool", ephemeral=True)

@client.tree.command()
async def del_weather(interaction: discord.Interaction):
    """Delete your weather pings"""
    ret_code = await wth.remove_user_from_dataframe(interaction.user.id)

    if ret_code:
        await interaction.response.send_message(ret_code, ephemeral=True)
    
    else:
        await interaction.response.send_message("Cool", ephemeral=True)

@client.tree.command()
async def tutorial_island(interaction: discord.Interaction):
    """Tells you how to do things"""
    await interaction.response.send_message(tutorial_text, ephemeral=True)

@client.tree.command()
async def list_responses(interaction: discord.Interaction):
    """Lists all the responses you've made, and their you-specific ID. Protip: use this to get the id of responses you want to remove"""
    async with dataframe_lock:
        responses = get_messages_owned_by(interaction.user.name)
    
    retstr = "\n- ".join(str(i) + ": " + response["response"] + " when " + response["condition"] for i, response in enumerate(responses))

    await interaction.response.send_message(retstr, ephemeral=True)

@client.tree.command()
async def remove_response(interaction: discord.Interaction, responsenum: int):
    """Delete a response by index. Protip: use list_responses to figure out what this means."""
    global tree

    async with dataframe_lock:
        responses = get_messages_owned_by(interaction.user.name)

        try:
            for _ in range(responsenum):
                next(responses)
        except StopIteration:
            await interaction.response.send_message("That's not a real message bro")
        
        idx = next(responses).name

        try:
            dataframe.drop(idx, inplace=True)
        except Exception as e:
            await interaction.response.send_message("Oops: " + str(e))

        await interaction.response.send_message("Condition removed :)")

        tree_obj = gen_tree_from_csv()

        dataframe.to_csv(cf.RESPONSE_FILENAME)
    
    async with message_lock:
        tree = tree_obj

# @client.tree.command()
# async def gen_graph(interaction: discord.Interaction):
#     """Gives you the current response tree state"""

#     try:
#         file = discord.File("/tmp/out.jpeg")

#         await interaction.response.send_message(file=file)
    
#     except:
#         await interaction.response.send_message("FILE MISSING!1!!!!")

# with LogObject("graph generation"):
#     tree.get_graph()

client.run(TOKEN)
