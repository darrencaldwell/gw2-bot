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
    async def on_ready(self):
        channel = self.get_channel(CHANNEL_ID)
        guild = self.get_guild(GUILD_ID)
        role = guild.get_role(ROLE_ID)

        cog = MyCog(self, channel, role)
        print(f'Logged on as {self.user} for channel {channel}')

    async def on_message(self, message):
        if message.author == client.user:
            return
        content = message.content.lower()
        channel = message.channel

        messages = tree.get_messages(message, content)
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

    # @tasks.loop(time=TIME)
    @tasks.loop(seconds=10)
    async def my_task(self):
        await asyncio.sleep(seconds_until_9am())
        date_string = f"{datetime.datetime.today().day}/{datetime.datetime.today().month}"
        print(f"Posting thread for {date_string}")
        message = await self.channel.send(build_message(self.role))
        thread = await message.create_thread(name=date_string, auto_archive_duration=1440)
        for react in EMOJI_MAP.keys():
            await message.add_reaction(react)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.command(name="addmessage")
async def addmessage(ctx, *args):
    args = "".join(args)
    

client = MyClient(intents=intents)
client.run(TOKEN)
