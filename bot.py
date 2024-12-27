import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
from async_timeout import timeout
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.volume = 1.0
        self.now_playing = None
        self.loop = False

queues = {}

def create_embed(title, description, color=discord.Color.blue()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="RCMbot Music", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    return embed

@bot.event
async def on_ready():
    print(f'Bot telah login sebagai {bot.user}')

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = MusicQueue()
    return queues[guild_id]

@bot.command()
async def search(ctx, *, query):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            embed = discord.Embed(
                title=" Search Result",
                description=f"**{info['title']}**",
                color=discord.Color.blue(),
                url=info['webpage_url']
            )
            if 'thumbnail' in info:
                embed.set_thumbnail(url=info['thumbnail'])
            embed.add_field(name="Duration", value=str(info.get('duration', 'N/A')))
            embed.add_field(name="Channel", value=info.get('uploader', 'N/A'))
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=create_embed(" Error", f"Error while searching: {str(e)}", discord.Color.red()))

@bot.command()
async def play(ctx, *, query):
    try:
        if not ctx.author.voice:
            await ctx.send(embed=create_embed(" Error", "You must be in a voice channel!", discord.Color.red()))
            return

        queue = get_queue(ctx.guild.id)
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            if not query.startswith('http'):
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            else:
                info = ydl.extract_info(query, download=False)

        queue.queue.append({
            'title': info['title'],
            'url': info['url'],
            'webpage_url': info.get('webpage_url', info['url']),
            'thumbnail': info.get('thumbnail', None)
        })

        embed = discord.Embed(
            title=" Added to Queue",
            description=f"**{info['title']}**",
            color=discord.Color.green(),
            url=info['webpage_url']
        )
        if 'thumbnail' in info:
            embed.set_thumbnail(url=info['thumbnail'])
        
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        
        await ctx.send(embed=embed)

        if not ctx.voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        print(f"Error: {e}")
        await ctx.send(embed=create_embed(" Error", f"An error occurred: {str(e)}", discord.Color.red()))

async def play_next(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue.queue:
        return
    
    try:
        song = queue.queue[0]
        queue.now_playing = song
        
        source = await discord.FFmpegOpusAudio.from_probe(
            song['url'],
            **FFMPEG_OPTIONS
        )
        
        def after_playing(error):
            if error:
                print(f"Error setelah pemutaran: {error}")
            if not queue.loop:
                queue.queue.popleft()
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        ctx.voice_client.play(source, after=after_playing)
        ctx.voice_client.source.volume = queue.volume
        
        await ctx.send(embed=create_embed(" Now Playing", song["title"], discord.Color.green()))

    except Exception as e:
        print(f"Error in play_next: {e}")
        await ctx.send(embed=create_embed(" Error", f"Error playing next song: {str(e)}", discord.Color.red()))

@bot.command(aliases=['np'])
async def nowplaying(ctx):
    queue = get_queue(ctx.guild.id)
    if queue.now_playing:
        embed = discord.Embed(
            title=" Now Playing",
            description=f"**{queue.now_playing['title']}**",
            color=discord.Color.green(),
            url=queue.now_playing['webpage_url']
        )
        embed.add_field(name="Volume", value=f"{int(queue.volume * 100)}%")
        embed.add_field(name="Loop", value=" On" if queue.loop else " Off")
        if queue.now_playing.get('thumbnail'):
            embed.set_thumbnail(url=queue.now_playing['thumbnail'])
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=create_embed(" Not Playing", "No song is currently playing", discord.Color.red()))

@bot.command(aliases=['q'])
async def queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue.queue:
        await ctx.send(embed=create_embed(" Queue Empty", "No songs in queue", discord.Color.red()))
        return

    description = ""
    for i, song in enumerate(queue.queue):
        if i == 0:
            description += f"**Now Playing:**\n {song['title']}\n\n"
        else:
            description += f"**{i}.** {song['title']}\n"

    embed = discord.Embed(
        title=" Music Queue",
        description=description,
        color=discord.Color.blue()
    )
    embed.add_field(name="Total Songs", value=str(len(queue.queue)))
    await ctx.send(embed=embed)

@bot.command()
async def volume(ctx, vol: int):
    if not ctx.voice_client:
        await ctx.send(embed=create_embed(" Error", "Bot is not playing music!", discord.Color.red()))
        return
    
    if not 0 <= vol <= 100:
        await ctx.send(embed=create_embed(" Error", "Volume must be between 0 and 100!", discord.Color.red()))
        return
    
    queue = get_queue(ctx.guild.id)
    queue.volume = vol / 100
    if ctx.voice_client.source:
        ctx.voice_client.source.volume = queue.volume
    
    await ctx.send(embed=create_embed(" Volume", f"Volume set to {vol}%", discord.Color.green()))

@bot.command(aliases=['s'])
async def skip(ctx):
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await ctx.send(embed=create_embed(" Error", "No song to skip!", discord.Color.red()))
        return
    
    ctx.voice_client.stop()
    await ctx.send(embed=create_embed(" Skipped", "Skipped current song", discord.Color.green()))

@bot.command()
async def loop(ctx):
    queue = get_queue(ctx.guild.id)
    queue.loop = not queue.loop
    await ctx.send(embed=create_embed(" Loop", f"Loop is now {'enabled' if queue.loop else 'disabled'}", discord.Color.green()))

@bot.command()
async def stop(ctx):
    queue = get_queue(ctx.guild.id)
    queue.queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send(embed=create_embed(" Stopped", "Music stopped and queue cleared", discord.Color.green()))

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send(embed=create_embed(" Paused", "Music paused", discord.Color.green()))

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send(embed=create_embed(" Resumed", "Music resumed", discord.Color.green()))

@bot.command()
async def musichelp(ctx):
    embed = discord.Embed(
        title=" RCMbot Music Commands",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name=" Basic Commands",
        value="`!play` - Play a song or add to queue\n"
              "`!stop` - Stop playing and clear queue\n"
              "`!pause` - Pause current song\n"
              "`!resume` - Resume paused song",
        inline=False
    )
    
    embed.add_field(
        name=" Queue Commands",
        value="`!queue (!q)` - Show current queue\n"
              "`!skip (!s)` - Skip current song\n"
              "`!loop` - Toggle loop mode",
        inline=False
    )
    
    embed.add_field(
        name=" Info & Control",
        value="`!nowplaying (!np)` - Show current song\n"
              "`!volume [0-100]` - Adjust volume\n"
              "`!search` - Search for a song",
        inline=False
    )
    
    embed.set_footer(text="RCMbot Music", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await ctx.send(embed=embed)

TOKEN = os.getenv('DISCORD_TOKEN')

bot.run(TOKEN)
