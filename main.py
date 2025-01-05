import os
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord import app_commands
from collections import deque

# Bot configuration
TOKEN = "YOUR_BOT_TOKEN_HERE"  # Bot token
MUSIC_DIR = "YOUR_MP3_DIRECTORY_HERE"  # Music directory
volume = 0.5  # Default volume (50%)

# Ensure directory exists
if not os.path.exists(MUSIC_DIR):
    raise FileNotFoundError(f"Directory '{MUSIC_DIR}' not found.")

# Initialize bot and tree
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=";", intents=intents)
tree = bot.tree

# Song queue
song_queue = deque()

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user.name}")

@tree.command(name="join", description="Joins the voice channel.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        embed = discord.Embed(
            title="Voice Channel",
            description=f"✅ Joined `{channel.name}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description="❌ You need to be in a voice channel first!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="leave", description="Leaves the voice channel.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        embed = discord.Embed(
            title="Voice Channel",
            description="✅ Disconnected from the voice channel.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description="❌ I'm not in a voice channel.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

def play_next(ctx):
    if song_queue:
        next_song = song_queue.popleft()
        source = discord.PCMVolumeTransformer(
            FFmpegPCMAudio(next_song, options="-vn -ar 48000 -ac 2 -b:a 192k"),
            volume=volume
        )
        ctx.guild.voice_client.play(source, after=lambda e: play_next(ctx))
        print(f"Playing next song: {os.path.basename(next_song)}")
    else:
        print("Queue is empty, playback stopped.")

@tree.command(name="play", description="Plays a song from the local folder or subfolders.")
@app_commands.describe(song="Name of the song to play.")
async def play(interaction: discord.Interaction, song: str):
    if not interaction.guild.voice_client:
        embed = discord.Embed(
            title="Error",
            description="❌ I'm not in a voice channel. Use `/join` first.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Search for the song in the directory and subdirectories
    song_path = None
    for root, _, files in os.walk(MUSIC_DIR):
        for file in files:
            if file.lower().startswith(song.lower()) and file.lower().endswith((".mp3", ".wav")):
                song_path = os.path.join(root, file)
                break
        if song_path:
            break

    if song_path:
        # Play audio if not already playing
        if not interaction.guild.voice_client.is_playing():
            source = discord.PCMVolumeTransformer(
                FFmpegPCMAudio(song_path, options="-vn -ar 48000 -ac 2 -b:a 192k"),
                volume=volume
            )
            interaction.guild.voice_client.play(source, after=lambda e: play_next(interaction))
            embed = discord.Embed(
                title="Now Playing",
                description=f"?? `{os.path.basename(song_path)}`",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
        else:
            # Add to queue if already playing
            song_queue.append(song_path)
            embed = discord.Embed(
                title="Queued",
                description=f"?? `{os.path.basename(song_path)}` added to the queue.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description=f"❌ Song `{song}` not found in the folder or subfolders.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="queue", description="Queues up the next song.")
@app_commands.describe(song="Name of the song to queue.")
async def queue(interaction: discord.Interaction, song: str):
    # Search for the song in the directory and subdirectories
    song_path = None
    for root, _, files in os.walk(MUSIC_DIR):
        for file in files:
            if file.lower().startswith(song.lower()) and file.lower().endswith((".mp3", ".wav")):
                song_path = os.path.join(root, file)
                break
        if song_path:
            break

    if song_path:
        # Add to queue
        song_queue.append(song_path)
        embed = discord.Embed(
            title="Queued",
            description=f"?? `{os.path.basename(song_path)}` added to the queue.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description=f"❌ Song `{song}` not found in the folder or subfolders.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="volume", description="Adjusts the playback volume.")
@app_commands.describe(level="Volume level (0 to 100).")
async def set_volume(interaction: discord.Interaction, level: int):
    global volume
    if 0 <= level <= 100:
        volume = level / 100
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = volume
        embed = discord.Embed(
            title="Volume Control",
            description=f"?? Volume set to {level}%",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description="❌ Volume must be between 0 and 100.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="stop", description="Stops the currently playing song.")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        song_queue.clear()  # Clear the queue
        embed = discord.Embed(
            title="Playback Stopped",
            description="⏹️ Playback has been stopped, and the queue has been cleared.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description="❌ No song is currently playing.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="help", description="Displays available commands and their descriptions.")
async def custom_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help - Command List",
        description="Here are the available commands:",
        color=discord.Color.purple()
    )
    embed.add_field(name="/join", value="Joins the voice channel.", inline=False)
    embed.add_field(name="/leave", value="Leaves the voice channel.", inline=False)
    embed.add_field(name="/play", value="Plays a song from the local folder or subfolders.", inline=False)
    embed.add_field(name="/queue", value="Queues up the next song.", inline=False)
    embed.add_field(name="/volume", value="Adjusts the playback volume.", inline=False)
    embed.add_field(name="/stop", value="Stops the currently playing song.", inline=False)
    embed.add_field(name="/help", value="Displays available commands and their descriptions.", inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
