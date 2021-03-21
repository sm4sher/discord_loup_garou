from discord.ext.commands import Bot
from discord.ext import tasks
from discord import HTTPException

from game import LgGame
from config import api_key 

import pickle

class LgBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.games = []
        self.first_start = True

    async def on_ready(self):
        if self.first_start:
            # too lazy to look if there's an event actually representing bot's start
            await self.delete_old_channels()
            self.first_start = False
        print('ready')

    async def delete_old_channels(self):
        """ When starting delete channels that were previously created and not deleted """
        self.load_chan_ids()
        for c in self.created_chan_ids:
            chan = self.get_channel(c)
            if chan is None:
                continue
            try:
                await chan.delete()
            except:
                pass
        self.created_chan_ids = []

    def save_chan_ids(self):
        with open('chans.pickle', 'wb+') as f:
            pickle.dump(self.created_chan_ids, f, pickle.HIGHEST_PROTOCOL)

    def load_chan_ids(self):
        with open('chans.pickle', 'rb') as f:
            self.created_chan_ids = pickle.load(f)



bot = LgBot(command_prefix='!')

@bot.command(name='start')
async def start_game(ctx):
    """Start a new game by sending a message asking who wants to play"""
    game = LgGame(ctx)
    ctx.bot.games.append(game)
    await game.send_start_dialog()

@bot.command(name='invite')
async def invite(ctx):
    ctx.send('If you want me to join your server, click this link')

bot.run(api_key)

"""
misc ideas:
- there will always be a voice chan if people want to talk during the game
but either with a command or by detecting it automatically, the bot will join
the voice chan and stream some cool sounds :) (ex wolves sound when they wake up)
- long term have other similar game (the resistance??...)
- advice to join the bot's server to find more players
- and how the fuck do i monetize that? 
extra cards maybe, extra games modes idk a lot of possiblities
- global and per-server stats/leaderboard
- IIRC bots can use custom emojis from any server so use that (for cards or votes for example)
- add some sleeps, typing... for suspens! it's all about ambiance

not ideas but things to do
-put max number of players (24?)
-have parameters by server (prefix, lang for example)
-translations
-when discord add features like /commands, buttons... intergrate it quickly in the bot
-not related to the code directly bu the invite needs to create a role with all perms (or at least manage channels)
-use @here to notify groups without creating roles for them (that would kinda kill the game lol)
-don't allow admins to play... since they can see all channels
-store all created channels ids somewhere and delete all of them at bot start (and empty the file) OK
"""
