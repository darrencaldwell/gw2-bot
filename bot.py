# every day at 9am create a post in specific channel
# apply certain emotes to the post
# create a thread with today's date
import asyncio
# https://discord.com/api/oauth2/authorize?client_id=1172277989103378454&permissions=34359740480&scope=bot

# bot.py
import os

import random

import discord
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv
import datetime
import declarative_tree as dt
from sympy import Not
from cond_parser import parse_string
import config as cf
from typing import Dict, Literal
from storage import LockingPandasRWer

from personality import amend, modify, columns

import pandas as pd

import time

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
VOICE_CHANNEL_ID = 1099793031139434496

#OSCAR TESTING
# CHANNEL_ID = 723899751732346964
# ROLE_ID = 1180661716107931658
# GUILD_ID = 723899751732346960
# WEATHER_CHANNEL_ID = 723899751732346964
# VOICE_CHANNEL_ID = 723899751732346965

TEST_VOICE_ID = 723899751732346965

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

dataframe_reader = LockingPandasRWer(cf.RESPONSE_FILENAME)

#dataframe = dataframe_reader.dataframe

async def gen_tree_from_csv():
    async with dataframe_reader.read as dataframe:
        condslist = [parsed_line for line in dataframe.iterrows() if (parsed_line := parse_cond_line(line[1]))]

    return dt.process_conds(condslist)

async def get_messages_owned_by(username: str, dataframe: pd.DataFrame):
    return (i[1] for i in dataframe.iterrows() if i[1]["author"] == username)

with LogObject("tree building"):
    tree = asyncio.run(gen_tree_from_csv())

message_lock = asyncio.Lock()

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

    async def on_message(self, message: discord.message.Message):
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
            response = await modify(response, message.author.id)
            await channel.send(response)



class MyCog(commands.Cog):
    def __init__(self, client: discord.Client, channel, other_channel, role):
        self.client = client
        self.channel = channel
        self.other_channel = other_channel

        self.role = role
        # self.my_task.start()
        self.adjust_probs.start()
        self.get_weather.start()
        self.play_audio.start()


    def cog_unxload(self):
        # self.my_task.cancel()
        self.adjust_probs.cancel()

    # @tasks.loop(seconds=10)
    # async def my_task(self):
    #     await asyncio.sleep(seconds_until_9am())
    #     date_string = f"{datetime.datetime.today().day}/{datetime.datetime.today().month}"
    #     print(f"Posting thread for {date_string}")
    #     message = await self.channel.send(build_message(self.role))
    #     thread = await message.create_thread(name=date_string, auto_archive_duration=1440)
    #     for react in EMOJI_MAP.keys():
    #         await message.add_reaction(react)

    @tasks.loop(hours=1)
    async def reset_mut_record(self):
        print(datetime.datetime.now().hour)
        print(my_mut_record.reset_time)
        if datetime.datetime.now().hour == my_mut_record.reset_time:
            my_mut_record.has_been_used = False

    @tasks.loop(minutes=1)
    async def play_audio(self):
        channel: discord.VoiceChannel = await self.client.fetch_channel(VOICE_CHANNEL_ID)

        members = channel.members

        if len(members) > 1:
            await play_audio(channel)
            await asyncio.sleep(200 + random.randint(0, 60*60*4)) 
    
    @tasks.loop(hours=1)
    async def adjust_probs(self):
        for author in dt.AUTHOR_DICT:
            dt.AUTHOR_DICT[author] = max(0, dt.AUTHOR_DICT[author] - adjust_prob_by)

    @tasks.loop(hours=1)
    async def pregenerate_graph(self):
        tree.get_graph()

    # @tasks.loop(hours=1)
    # async def message_connor(self):
    #     channel = await self.client.fetch_channel(1099793030678069341)
    #     user = await self.client.fetch_user(511552638853185536)

    #     at_connor = user.mention

    #     await channel.send(f"Hello {user.mention}! It's me, Queen Jennah. I would really like it if you killed Coathe. Thanks.")

    @tasks.loop(seconds=10)
    async def get_weather(self):
        await asyncio.sleep(seconds_until_9am()-3*60*60)
        messages = await wth.generate_messages()

        await asyncio.sleep(3*60*60)

        for user, message in messages.items():
            if message:
                try:
                    user = await self.client.fetch_user(user)
                except:
                    continue
                
                message = await modify(message, user.id)
                
                await self.other_channel.send(user.mention)
                await self.other_channel.send(message)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

client = MyClient(intents=intents)

with open("tutorial.md", "r") as f:
    tutorial_text =  f.read()

async def play_audio(channel: discord.VoiceChannel, src: str | None = None):
    vc = await channel.connect()

    if src == None:
        src = random.choice(os.listdir("audio/"))
    
    vc.play(
        discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
            source = "audio/" + src)))

    while vc.is_playing():
        await asyncio.sleep(0.5)

    await vc.disconnect() 

# @client.tree.command()
# async def test_audio(interaction: discord.Interaction):
#     channel = await client.fetch_channel(TEST_VOICE_ID)

#     print(type(channel))

#     await interaction.response.send_message("Test complete")

#     await play_audio(channel)

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

    async with dataframe_reader.edit as dataframe:
        dataframe.loc[len(dataframe)] = {"response": response, "condition": condition, "author": interaction.user.name}
        tree_obj = gen_tree_from_csv()

    async with message_lock:
        tree = await tree_obj

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
    ret = await modify(tutorial_text, interaction.user.id)
    await interaction.response.send_message(ret, ephemeral=True)

@client.tree.command()
async def list_responses(interaction: discord.Interaction):
    """Lists all the responses you've made, and their you-specific ID. Protip: use this to get the id of responses you want to remove"""
    async with dataframe_reader.read as dataframe:
        responses = await get_messages_owned_by(interaction.user.name, dataframe)
    
    retstr = "\n- ".join(str(i) + ": " + response["response"] + " when " + response["condition"] for i, response in enumerate(responses))

    await interaction.response.send_message(retstr, ephemeral=True)

@client.tree.command(description="Sets Jennah's feelings towards you. Allowed values: " + ", ".join(columns["personality"].all))
async def set_personality(interaction: discord.Interaction, personality: str):
    ret = await amend(interaction.user.id, personality=personality)

    if ret:
        message = "Request granted, {nickname}"
        message = await modify(message, interaction.user.id)
        await interaction.response.send_message(message, ephemeral=True)

    else:
        message = "Could not do, {nickname}"
        message = await modify(message, interaction.user.id)
        await interaction.response.send_message(message, ephemeral=True)

@client.tree.command()
async def remove_response(interaction: discord.Interaction, responsenum: int):
    """Delete a response by index. Protip: use list_responses to figure out what this means."""
    global tree

    async with dataframe_reader.edit as dataframe:
        responses = await get_messages_owned_by(interaction.user.name, dataframe)
        
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
    
    async with message_lock:
        tree = tree_obj

client.run(TOKEN)
