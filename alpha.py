import discord
import logging
import os
import yt_dlp as yt
import asyncio
import urllib.parse
import urllib.request
import re
import datetime

from dotenv import load_dotenv
from itertools import cycle
from discord.ext import commands,tasks

def run():
    #logger init
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log = logging.getLogger(__name__)


    #Init
    load_dotenv(r"music-bot\.env")
    TOKEN: str = os.getenv("TOKEN")
    Command_Prefix = ">"
    client = commands.Bot(command_prefix = Command_Prefix, intents = discord.Intents.all())
    bot_status = cycle([f'{Command_Prefix}help', 'discord.py', 'jamming...'])
    
    client.remove_command("help")


    #vars
    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    is_playing: bool = False
    yt_dl_options = {"format":"bestaudio/best"}
    ytdl = yt.YoutubeDL(yt_dl_options)

    ffmpeg_options = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5","options": "-vn -filters:a 'volume=0.25'"}

    @client.event
    async def on_ready():
        log.info(f'Logged in as: {client.user.name}')
        log.info(f'BOT ID: {client.user.id}')
        log.info(f'On Servers: {len(client.guilds)}')
        log.info(f'Discord.py version: {discord.__version__}')
        change_status.start()
    
    @tasks.loop(seconds=15)
    async def change_status():
        await client.change_presence(activity=discord.Game(next(bot_status)))

    async def play_next(ctx):
        if queues[ctx.guild.id] != []:
            link = queues[ctx.guild.id].pop(0)
            await play(ctx, link=link)  

    @client.command(name="play", aliases=["p"])
    async def play(ctx: commands.Context, link: str):
        if not ctx.author.voice:
            await ctx.reply("```Please Join a Voice Channel.```")

        # if is_playing:
        #     await queue(ctx, link)
        #     return

        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.author.guild.id] = voice_client

        except Exception as error:
            log.error(f"{error}")
        
        try:
            if youtube_base_url not in link:
                query_string = urllib.parse.urlencode({
                    "search_query": link
                })

                content = urllib.request.urlopen( youtube_results_url + query_string )

                result:list = re.findall(r'/watch\?v=(.{11})', content.read().decode())[0]

                link = youtube_watch_url + result
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

            song = data["url"]
            player = discord.FFmpegPCMAudio(song, **ffmpeg_options)
            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

        except Exception as error:
            log.error(f"{error}")

            is_playing = False

            await clear(ctx)
        
        # else:
        #     is_playing = True
    
    @client.command(name = "skip")
    async def skip(ctx: commands.Context):

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
    
    @client.command(name = "clear", aliases = ["c", "C"])
    async def clear(ctx: commands.Context):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()

            embed = discord.Embed(title= "Queue Cleared⏰", description= "```The Music Queue has been cleared.```", color= discord.Color.green(), timestamp= datetime.datetime.now())
            embed.set_author(name= f"Issued by: {ctx.author.name}", icon_url= ctx.author.avatar.url)
            await ctx.send(embed= embed)

        else:
            embed = discord.Embed(title= "Queue Was Not Cleared!⏰", description= "```The queue is already clear.```", color= discord.Color.red(), timestamp= datetime.datetime.now())
            embed.set_author(name= f"Issued by: {ctx.author.name}", icon_url= ctx.author.avatar.url)
            await ctx.send(embed= embed)

    @client.command(name = "pause")
    async def pause(ctx: commands.Context):
        try:
            voice_clients[ctx.guild.id].pause()

            embed = discord.Embed(title= "💽Player Paused.🛑", description= "```Player has been paused.```", color= discord.Color.magenta(), timestamp= datetime.datetime.now())
            embed.set_author(name= f"Issued by: {ctx.author.name}", icon_url= ctx.author.avatar.url)
            await ctx.send(embed = embed)
        
        except Exception as error:
            log.error(f"{error}")
    
    @client.command(name="resume", aliases = ["r", "res"])
    async def resume(ctx: commands.Context):
        try:
            voice_clients[ctx.guild.id].resume()
        
            embed = discord.Embed(title= "💽Player Resumed.▶️", description= "```Player has been Resumed.```", color= discord.Color.magenta(), timestamp= datetime.datetime.now())
            embed.set_author(name= f"Issued by: {ctx.author.name}", icon_url= ctx.author.avatar.url)
            await ctx.send(embed = embed)

        except Exception as e:
            print(e)

    @client.command(name="stop", aliases = ["s", "S"])
    async def stop(ctx: commands.Context):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]

            embed = discord.Embed(title= "💽Player Stopped.🛑", description= "```Player has been Stopped.```", color= discord.Color.magenta(), timestamp= datetime.datetime.now())
            embed.set_author(name= f"Issued by: {ctx.author.name}", icon_url= ctx.author.avatar.url)
            await ctx.send(embed = embed)

        except Exception as e:
            print(e)

    @client.command(name="queue")
    async def queue(ctx: commands.Context, url: str):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)

        embed = discord.Embed(title= "+ Added To Queue +", description= f"```Added to Queue.```\nLink: [{url}]", color= discord.Color.magenta(), timestamp= datetime.datetime.now())
        embed.set_author(name= f"Issued by: {ctx.author.name}", icon_url= ctx.author.avatar.url)
        await ctx.send(embed = embed)
    
    client.run(token = TOKEN)

if __name__ == "__main__":
    pass