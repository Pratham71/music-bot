import discord
import logging
import os
import yt_dlp as yt
import asyncio
import urllib.parse
import re
import datetime

from dotenv import load_dotenv
from itertools import cycle
from discord.ext import commands, tasks

# Logger initialization
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Load .env variables
load_dotenv(r"music-bot\.env")
TOKEN = os.getenv("TOKEN")
Command_Prefix = ">"
client = commands.Bot(command_prefix=Command_Prefix, intents=discord.Intents.all())
bot_status = cycle([f'{Command_Prefix}help', 'discord.py', 'jamming...'])

client.remove_command("help")

# Global Variables
queues = {}
voice_clients = {}
is_playing = False
youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='
yt_dl_options = {
    "format": "bestaudio[ext=m4a]/bestaudio",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "m4a",
        "preferredquality": "256",  # 64 kbps for lower bitrate
    }],
}
ytdl = yt.YoutubeDL(yt_dl_options)
ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 128k",
}


@client.event
async def on_ready():
    log.info(f'Logged in as: {client.user.name} (ID: {client.user.id})')
    change_status.start()

@tasks.loop(seconds=15)
async def change_status():
    await client.change_presence(activity=discord.Game(next(bot_status)))

async def play_next(ctx):
    if queues.get(ctx.guild.id):
        link = queues[ctx.guild.id].pop(0)
        await play(ctx, link=link)  # Play the next song in queue

@client.command(name="play", aliases=["p"])
async def play(ctx: commands.Context, link: str):
    global is_playing
    if not ctx.author.voice:
        return await ctx.reply("```Please join a voice channel.```")

    if is_playing:
        await queue(ctx, link)
        return

    try:
        voice_client = await ctx.author.voice.channel.connect()
        voice_clients[ctx.guild.id] = voice_client

    except Exception as error:
        log.error(f"Connection error: {error}")

    try:
        if youtube_base_url not in link:
            query_string = urllib.parse.urlencode({"search_query": link})
            content = urllib.request.urlopen(youtube_results_url + query_string)
            result = re.findall(r'/watch\?v=(.{11})', content.read().decode())[0]
            link = youtube_watch_url + result

        data = ytdl.extract_info(link, download=False)
        song_url = data["url"]
        player = discord.FFmpegPCMAudio(song_url, **ffmpeg_options, executable= os.getenv("ffmpeg_Path"))
        
        voice_clients[ctx.guild.id].play(
            player,
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
        )
        is_playing = True

    except Exception as error:
        log.error(f"Playback error: {error}")
        is_playing = False
        await clear(ctx)

# @client.command(name="skip", aliases=["s", "S"])
# async def skip(ctx: commands.Context):
#     if ctx.guild.id in voice_clients:
#         voice_clients[ctx.guild.id].stop()
#         await play_next(ctx)

@client.command(name="clear", aliases=["c", "C"])
async def clear(ctx: commands.Context):
    global is_playing
    if ctx.guild.id in queues:
        queues[ctx.guild.id].clear()
        is_playing = False
        embed = discord.Embed(title="Queue Cleared⏰", description="```The Music Queue has been cleared.```", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Queue Was Not Cleared!⏰", description="```The queue is already clear.```", color=discord.Color.red())
        await ctx.send(embed=embed)

@client.command(name="pause")
async def pause(ctx: commands.Context):
    try:
        voice_clients[ctx.guild.id].pause()
        await ctx.send(embed=discord.Embed(title="💽 Player Paused 🛑", description="```Player has been paused.```", color=discord.Color.magenta()))
    except Exception as error:
        log.error(f"Pause error: {error}")

@client.command(name="resume", aliases=["r", "res"])
async def resume(ctx: commands.Context):
    try:
        voice_clients[ctx.guild.id].resume()
        await ctx.send(embed=discord.Embed(title="💽 Player Resumed ▶️", description="```Player has been resumed.```", color=discord.Color.magenta()))
    except Exception as e:
        log.error(f"Resume error: {e}")

@client.command(name="stop", aliases=["s", "S"])
async def stop(ctx: commands.Context):
    try:
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
        await ctx.send(embed=discord.Embed(title="💽 Player Stopped 🛑", description="```Player has been stopped.```", color=discord.Color.magenta()))
    except Exception as e:
        log.error(f"Stop error: {e}")

@client.command(name="queue")
async def queue(ctx: commands.Context, url: str):
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    queues[ctx.guild.id].append(url)
    await ctx.send(embed=discord.Embed(title="+ Added To Queue +", description=f"```Added to Queue: {url}```", color=discord.Color.magenta()))

@client.command(name = "stop_bot")
@commands.is_owner()
async def stop_bot(ctx:commands.Context):
    await ctx.send("Stopping...")
    await client.close()

def run():
    client.run(token = TOKEN)
    
