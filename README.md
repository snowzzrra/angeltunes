# Angel Tunes
<div style="text-align: center">
    <img src="resources/mih.png"/>
    <p>YouTube, Spotify e até arquivos locais. Angel Tunes toca musica de qualquer lugar.</p>
</div>

## Variáveis de Ambiente

Para rodar esse projeto, você vai precisar adicionar as seguintes variáveis de ambiente no seu .env

`DISCORD_TOKEN`

`SPOTIFY_CLIENT_ID`

`SPOTIFY_CLIENT_SECRET`

Além disso, você precisa ter o [ffmpeg](https://www.ffmpeg.org) nas variáveis de sistema.
## Rodando localmente

Clone o projeto

```bash
git clone https://github.com/snowzzrra/angeltunes
```

Entre no diretório do projeto

```bash
cd angeltunes
```

Instale as dependências

```bash
pip install discord.py[voice] yt-dlp pytube spotipy deezer-api requests python-dotenv
```

Inicie o bot

```bash
python bot_main.py
```


## Melhorias necessárias

- !repeat não funciona.
- Erros na inserção de playlists pelo Spotify.
- Suporte ao Deezer e Soundcloud.
- Velocidade de download de musicas.

## Autores

- [Guilherme Paim Motta](https://github.com/snowzzrra)
- Sarah

