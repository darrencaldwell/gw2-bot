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
from parser import parse_string
import config as cf
import csv
from typing import List

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
TIME = datetime.time(hour=9),

# TESTING
#CHANNEL_ID = 1172277801165004926
#ROLE_ID = 1173352152568172685
#GUILD_ID = 1172277800493928582

# REAL
CHANNEL_ID = 1166772628216893620
ROLE_ID = 1168850068665794661
GUILD_ID = 1099793030678069338

#OSCAR TESTING
CHANNEL_ID = 723899751732346964
ROLE_ID = 1180661716107931658
GUILD_ID = 723899751732346960

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

condslist = [
    dt.Condition("Darren is never wrong, respect your old GMs", dt.Contains("darren")),
    dt.Condition("Talking about _toes_, are we. :eyes:", dt.Contains("feet") | dt.Contains("foot") | dt.Contains("toe")),
    dt.Condition("Please refer to Tom by his proper title, Supreme High Guildmaster Tom", dt.Contains("tom") & Not(dt.Contains("supreme high guildmaster tom"))),
]

def parse_cond_line(line: List[str]) -> dt.Condition:
    print(line)
    try:
        cond = dt.Condition(condition = parse_string(line[1]) & dt.AuthorRateLimit(line[2]), message = line[0])
    except Exception as e:
        print("Failed to load line " + str(line) + " " + str(e))
        return None

    return cond

with open(cf.RESPONSE_FILENAME, "r") as f:
    csvreader = csv.reader(f)
    condslist = [parsed_line for line in csvreader if (parsed_line := parse_cond_line(line))]

print(condslist)
tree = dt.process_conds(condslist)

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

        cog = MyCog(self, channel, role)
        print(f'Logged on as {self.user} for channel {channel}')

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)

    async def on_message(self, message):
        if message.author == client.user:
            return
        content = message.content.lower()
        channel = message.channel

        messages = tree.get_messages(message)
        for response in messages:
            await channel.send(response)


class MyCog(commands.Cog):
    def __init__(self, client, channel, role):
        self.client = client
        self.channel = channel
        self.role = role
        self.my_task.start()

    def cog_unxload(self):
        self.my_task.cancel()

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
    async def adjust_probs(self):
        for author in dt.AUTHOR_DICT:
            dt.AUTHOR_DICT[author] = max(0, dt.AUTHOR_DICT[author] - adjust_prob_by)

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
        parsed_condition = parse_string(condition)
    
    except Exception as e:
        await interaction.response.send_message(tutorial_text, ephemeral=True)
        return
    
    with open(cf.RESPONSE_FILENAME, "a") as f:
        csvwriter = csv.writer(f)
        print("Adding: " + str(condition) + " from " + interaction.user.name)
        csvwriter.writerow([response, condition, interaction.user.name])

    parsed_condition = parsed_condition & dt.AuthorRateLimit(interaction.user.name)

    condslist.append(dt.Condition(response, parsed_condition))
    tree = dt.process_conds(condslist)
    
    await interaction.response.send_message("All good :) ")

@client.tree.command()
async def tutorial_island(interaction: discord.Interaction):
    await interaction.response.send_message(tutorial_text, ephemeral=True)


client.run(TOKEN)
