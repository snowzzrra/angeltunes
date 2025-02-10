import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
from pytube import YouTube
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configurações de áudio
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'extractor_args': {
        'youtube': {
            'skip': [
                'dash',
                'hls'
            ]
        }
    }
}

# Inicialização de APIs
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')),
    retries=3,
    status_forcelist=[429, 500, 502, 503, 504]
)

# Fila de músicas por servidor
queues = {}

class QueueItem:
    def __init__(self):
        self.queue = []
        self.repeat = False
        self.loop = False

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

class MusicSource:
    def __init__(self, source, title, url):
        self.source = source
        self.title = title
        self.url = url

    def create_player(self):
        return self.source

async def play_next(ctx):
    if ctx.guild.id not in queues:
        return
    
    queue = queues[ctx.guild.id]
    
    if queue.repeat and queue.queue:
        current = queue.queue[0]
        queue.queue.append(current)
    
    if queue.queue:
        player = queue.queue.pop(0)
        audio_source = player.create_player()
        ctx.voice_client.play(audio_source, after=lambda e: bot.loop.create_task(play_next(ctx)))
        await ctx.send(f'🎶 Tocando agora: **{player.title}**')

async def process_source(ctx, url):
    voice_client = ctx.voice_client

    # Arquivo local
    if os.path.exists(url):
        return MusicSource(
            discord.FFmpegPCMAudio(url),
            os.path.basename(url),
            url
        )

    # YouTube (vídeo ou playlist)
    if 'youtube.com' in url or 'youtu.be' in url:
        return await process_youtube(ctx, url)

    # Spotify (track, album ou playlist)
    if 'spotify.com' in url:
        return await process_spotify(ctx, url)

    # Busca genérica
    if '://' not in url:
        return await search_youtube(ctx, url)

    return None

async def process_youtube(ctx, url):
    try:
        ydl_opts = YDL_OPTIONS.copy()
        if 'list=' in url:
            ydl_opts['noplaylist'] = False

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:  # Playlist
                entries = info['entries']
                await ctx.send(f"🎵 Adicionando playlist: **{info['title']}** ({len(entries)} músicas)")
                return [MusicSource(
                    discord.FFmpegOpusAudio(entry['url'], **FFMPEG_OPTIONS),
                    entry['title'],
                    entry['webpage_url']
                ) for entry in entries if entry]
            
            return MusicSource(
                discord.FFmpegOpusAudio(info['url'], **FFMPEG_OPTIONS),
                info['title'],
                info['webpage_url']
            )
            
    except Exception as e:
        await ctx.send(f"Erro no YouTube: {str(e)}")
        return None

async def process_spotify(ctx, url):
    try:
        if 'track' in url:
            track = sp.track(url)
            search_query = f"{track['name']} {track['artists'][0]['name']}"
            return await search_youtube(ctx, search_query)
        
        elif 'playlist' in url:
            results = sp.playlist_items(url)
            tracks = results['items']
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            
            await ctx.send(f"🎵 Adicionando playlist: {sp.playlist(url)['name']} ({len(tracks)} músicas)")
            return [await search_youtube(ctx, f"{item['track']['name']} {item['track']['artists'][0]['name']}") for item in tracks]
        
        elif 'album' in url:
            album = sp.album(url)
            results = sp.album_tracks(url)
            tracks = results['items']
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            
            await ctx.send(f"🎵 Adicionando álbum: **{album['name']}** ({len(tracks)} músicas)")
            return [await search_youtube(ctx, f"{track['name']} {track['artists'][0]['name']}") for track in tracks]
        
        return None
        
    except Exception as e:
        await ctx.send(f"Erro no Spotify: {str(e)}")
        return None

async def search_youtube(ctx, query):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info or not info['entries']:
                await ctx.send("Nenhum resultado encontrado")
                return None
            
            video = info['entries'][0]
            return MusicSource(
                discord.FFmpegOpusAudio(video['url'], **FFMPEG_OPTIONS),
                video['title'],
                video['webpage_url']
            )
    except Exception as e:
        await ctx.send(f"Erro na busca: {str(e)}")
        return None

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("Você precisa estar em um canal de voz!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()

@bot.command()
async def play(ctx, *, url):
    if not ctx.voice_client:
        await ctx.invoke(join)
    
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = QueueItem()
    
    try:
        result = await process_source(ctx, url)
        
        if not result:
            await ctx.send("Fonte de áudio não suportada!")
            return
            
        if isinstance(result, list):  # Playlist
            queues[ctx.guild.id].queue.extend(result)
            await ctx.send(f"✅ {len(result)} músicas adicionadas à fila!")
        else:  # Música única
            queues[ctx.guild.id].queue.append(result)
            await ctx.send(f"✅ **{result.title}** adicionada à fila!")
        
        if not ctx.voice_client.is_playing():
            await play_next(ctx)
            
    except Exception as e:
        await ctx.send(f"Erro: {str(e)}")

@bot.command()
async def pause(ctx):
    ctx.voice_client.pause()
    await ctx.send("⏸️ Pausado")

@bot.command()
async def resume(ctx):
    ctx.voice_client.resume()
    await ctx.send("▶️ Retomando")

@bot.command()
async def stop(ctx):
    ctx.voice_client.stop()
    queues[ctx.guild.id] = []
    await ctx.send("⏹️ Parado e limpou a fila")

@bot.command()
async def skip(ctx):
    ctx.voice_client.stop()
    await ctx.send("⏭️ Pulando música atual")
    await play_next(ctx)

@bot.command()
async def queue(ctx):
    if not queues.get(ctx.guild.id):
        await ctx.send("A fila está vazia!")
        return
    
    queue_list = [f"{i+1}. {item.title}" for i, item in enumerate(queues[ctx.guild.id])]
    await ctx.send("**Fila de reprodução:**\n" + "\n".join(queue_list))

@bot.command()
async def repeat(ctx):
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = QueueItem()
    
    queues[ctx.guild.id].repeat = not queues[ctx.guild.id].repeat
    await ctx.send(f"🔂 Repeat {'ativado' if queues[ctx.guild.id].repeat else 'desativado'}")

@bot.command()
async def shuffle(ctx):
    if ctx.guild.id not in queues or len(queues[ctx.guild.id].queue) < 2:
        await ctx.send("Não há músicas suficientes para embaralhar!")
        return
    
    import random
    current = queues[ctx.guild.id].queue.pop(0)
    random.shuffle(queues[ctx.guild.id].queue)
    queues[ctx.guild.id].queue.insert(0, current)
    await ctx.send("🔀 Fila embaralhada com sucesso!")

bot.run(os.getenv('DISCORD_TOKEN'))