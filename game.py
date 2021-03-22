from discord.ext import tasks
from discord import HTTPException, Embed, PermissionOverwrite

import logging
import random
from functools import reduce

import utils
from react_dialog import ReactDialog
from start_dialog import StartDialog
from villager import Villager
from wolf import Wolf
from seer import Seer
from witch import Witch
from cupidon import Cupidon
from thief import Thief
from hunter import Hunter

class LgGame():
    # remember to change decorator args as well (not sure if there's a better way)
    START_DIALOG_UPDATE_INTERVAL = 1
    START_DIALOG_MIN_TIME = 10
    START_DIALOG_MAX_TIME = 500 # Cancel after a certain period
    MIN_PLAYERS_NB = 1
    MAX_PLAYERS_NB = 24
    START_DIALOG_MSG = (
        '{game_starter} a lancé une partie!\n'
        'Cliquez sur le loup pour participer\n'
        'Joueurs: **{nb_players}/{nb_players_min}**\n'
        '{status}'
    )
    START_DIALOG_REACTION_EMOJI = '🐺'

    def __init__(self, initial_ctx):
        self.initial_ctx = initial_ctx
        self.bot = initial_ctx.bot
        # could add game_starter directly but wld be deleted during update
        self.players = []

    async def send_start_dialog(self):
        self.start_dialog = StartDialog(
            self.initial_ctx.author, self.MIN_PLAYERS_NB,
            self.initial_ctx.channel, self.bot)
        await self.start_dialog.start()
        self.update_start_dialog.start()

    @tasks.loop(seconds=1)
    async def update_start_dialog(self):
        if not await self.start_dialog.update():
            return
        self.update_start_dialog.stop()
        self.players = await self.start_dialog.get_players()
        # if there are too many players just take the first ones
        self.players = self.players[:self.MAX_PLAYERS_NB]
        if self.MIN_PLAYERS_NB <= len(self.players) <= self.MAX_PLAYERS_NB:
            # Game can start
            await self.init_game()

    def distribute_cards(self):
        nb_p = len(self.players)
        if nb_p < 0: #8
            # Variante permettant de jouer avec peu de joueurs:
            # https://www.trictrac.net/forum/sujet/les-loups-garous-de-thiercelieux-variante-5-joueurs-et
            # Could also try another game like The resistance?
            raise Exception("Not implemented")
        else:
            self.cards = 2*['wolf'] + 3*['villager'] + ['seer', 'witch', 'cupidon']
        if nb_p >= 9:
            self.cards.append('hunter')
        if nb_p >= 10:
            self.cards.append('thief')
        if nb_p >= 12:
            self.cards.append('wolf')
        if nb_p >= 18:
            self.cards.append('wolf')
        nb_cards = nb_p + (2 if nb_p >= 12 else 0)
        self.cards += ['villager'] * (nb_cards - len(self.cards))
        random.shuffle(self.cards)

        self.villagers = []
        self.wolves = []
        self.lovers = []
        self.seer = None
        self.witch = None
        self.cupidon = None
        self.hunter = None
        self.thief = None
        for p in self.players:
            c = self.cards.pop()
            if c == 'villager':
                self.villagers.append(Villager(p, self))
            elif c == 'wolf':
                v = Wolf(p, self)
                self.wolves.append(v)
                self.villagers.append(v)
            elif c == 'seer':
                self.seer = Seer(p, self)
                self.villagers.append(self.seer)
            elif c == 'witch':
                self.witch = Witch(p, self)
                self.villagers.append(self.witch)
            elif c == 'cupidon':
                self.cupidon = Cupidon(p, self)
                self.villagers.append(self.cupidon)
            elif c == 'hunter':
                self.hunter = Hunter(p, self)
                self.villagers.append(self.hunter)
            elif c == 'thief':
                self.thief = Thief(p, self)
                self.villagers.append(self.thief)

    async def create_chan(self, name, users, category=False):
        ow = {
            self.initial_ctx.guild.default_role: PermissionOverwrite(read_messages=False),
            **{u: PermissionOverwrite(read_messages=True) for u in users}
        }
        if category:
            chan = await self.initial_ctx.guild.create_category(
                name, overwrites=ow)
        else:
            chan = await self.initial_ctx.guild.create_text_channel(
                name, category=self.ctg, overwrites=ow)
        self.bot.created_chan_ids.append(chan.id)
        self.bot.save_chan_ids()
        return chan

    async def init_game(self):
        """Initialize game model, create needed channels..."""
        self.distribute_cards()

        self.ctg = await self.create_chan(
            "Partie de Loup Garou", 
            [v.user for v in self.villagers],
            category=True)

        self.main_chan = await self.create_chan(
            "Place de Thiercelieu", [v.user for v in self.villagers])

        self.wolves_chan = await self.create_chan(
            "Loups", [w.user for w in self.wolves])

        # Create private chans for everyone.
        for v in self.villagers:
            v.channel = await self.create_chan(
                "Privé", [v.user])
            await v.send_card()

        self.turn = 1
        self.next_step = self.STEP_START
        self.next_death_step = self.DEATH_STEP_MAYOR
        self.wolves_victim = None
        self.witch_victim = None
        self.witch_saved = False
        self.dying = []
        self.process_deaths = False
        # finally, launch the mayor election then first night
        await self.start_election()

    async def start_election(self):
        txt = (
            "Il est temps d'élire un Maire! Le vote du maire compte double.\n"
            "{status}\n"
            "{choices}"
        )
        self.election_candidates = utils.emoji_dict(self.villagers)
        self.election_dialog = ReactDialog(
            self.main_chan, self.bot, choices=self.election_candidates, 
            title="Élection", desc=txt)
        await self.election_dialog.start()
        self.update_election.start()

    @tasks.loop(seconds=1)
    async def update_election(self):
        if not await self.election_dialog.update():
            return
        # Election has ended
        self.update_election.stop()
        winner_emo = await self.election_dialog.get_winner()
        if winner_emo is False:
            # no winner = no mayor
            await self.main_chan.send("Aucun maire n'a été élu.")
            await self.next()
            return
        winner = self.election_candidates[winner_emo]
        winner.is_mayor = True
        await self.main_chan.send("{} a été élu maire. Bravo!".format(
            winner.user.mention))
        await self.next()
    
    STEP_START = 0
    STEP_THIEF = 1
    STEP_CUPIDON = 2
    STEP_LOVERS = 3
    STEP_SEER = 4
    STEP_WOLVES = 5
    STEP_WITCH = 6
    STEP_WOLVES_DEATH = 7
    STEP_WITCH_DEATH = 8
    STEP_VOTE = 9
    STEP_END = 10

    async def next(self):
        """ Start appropriate actions depending on turn/step """
        if self.process_deaths and self.dying:
            await self.death_next()
            return
        print("next step:", self.next_step)
        if self.next_step == self.STEP_START:
            # New turn just started
            if self.turn == 1:
                self.next_step = self.STEP_THIEF  
            else:
                self.next_step = self.STEP_SEER
            await self.main_chan.send("Les villageois de Thiercelieux s'endorment paisiblement...")
            await self.next()
        elif self.next_step == self.STEP_THIEF:
            self.next_step = self.STEP_CUPIDON
            if self.thief is not None:
                await self.thief.play()
            else:
                await self.next()
        elif self.next_step == self.STEP_CUPIDON:
            self.next_step = self.STEP_LOVERS
            if self.cupidon is not None:
                await self.cupidon.play()
            else:
                await self.next()
        elif self.next_step == self.STEP_LOVERS:
            self.next_step = self.STEP_SEER
            await self.play_lovers()
        elif self.next_step == self.STEP_SEER:
            self.next_step = self.STEP_WOLVES
            if self.seer is not None:
                await self.seer.play()
            else:
                await self.next()
        elif self.next_step == self.STEP_WOLVES:
            self.next_step = self.STEP_WITCH
            await self.play_wolves()
        elif self.next_step == self.STEP_WITCH:
            self.next_step = self.STEP_WOLVES_DEATH
            if self.witch is not None:
                await self.witch.play()
            else:
                await self.next()
        elif self.next_step == self.STEP_WOLVES_DEATH:
            self.next_step = self.STEP_WITCH_DEATH
            await self.play_wolves_death()
        elif self.next_step == self.STEP_WITCH_DEATH:
            self.next_step = self.STEP_VOTE
            await self.play_witch_death()
        elif self.next_step == self.STEP_VOTE:
            self.next_step = self.STEP_END
            await self.play_vote()
        elif self.next_step == self.STEP_END:
            self.next_step = self.STEP_START
            await self.end_turn()

    # distinct steps used when someone die for any reason
    DEATH_STEP_MAYOR = 0
    DEATH_STEP_HUNTER = 1
    DEATH_STEP_LOVER = 2
    DEATH_STEP_END = 3

    async def death_next(self):
        if not self.dying:
            await self.next()
            return
        print("next death step:", self.next_death_step)
        dying = self.dying[0]
        if self.next_death_step == self.DEATH_STEP_MAYOR:
            self.next_death_step = self.DEATH_STEP_HUNTER
            await dying.mayor_death()
        elif self.next_death_step == self.DEATH_STEP_HUNTER:
            self.next_death_step = self.DEATH_STEP_LOVER
            await dying.hunter_death()
        elif self.next_death_step == self.DEATH_STEP_LOVER:
            self.next_death_step = self.DEATH_STEP_END
            await dying.lover_death()
        elif self.next_death_step == self.DEATH_STEP_END:
            self.next_death_step = self.DEATH_STEP_MAYOR
            self.dying = self.dying[1:] # he's dead now
            print("is he fucking dead jim??", self.dying)
            dying.alive = False # yeah he's really dead jim
            if not self.dying:
                self.process_deaths = False # we're done for now
            await self.next()

    def kill(self, player):
        """ Add player to self.dying but check that they're not already dying"""
        if player in self.dying:
            return
        self.dying.append(player)

    async def play_lovers(self):
        if not self.lovers or len(self.lovers) != 2:
            await self.next()
            return
        self.lovers_chan = await self.create_chan(
            "Amoureux", self.lovers)
        await self.lovers_chan.send("X et X vous êtes amoureux! Survivez ensemble pour gagner")
        await self.next()

    async def play_wolves(self):
        await self.main_chan.send("Les loups garous se réveillent :o")
        txt = (
            "Qui voulez vous dévorer cette nuit?\n"
            "{status}\n"
            "{choices}"
        )
        self.wolves_preys = utils.emoji_dict(
            [v for v in self.villagers if v.alive and not isinstance(v, Wolf)])
        self.wolves_dialog = ReactDialog(
            self.wolves_chan, self.bot, choices=self.wolves_preys, 
            title="Chasse", desc=txt)
        await self.wolves_dialog.start()
        self.update_wolves_dialog.start()

    @tasks.loop(seconds=1)
    async def update_wolves_dialog(self):
        if not await self.wolves_dialog.update():
            return
        self.update_wolves_dialog.stop()
        victim_emo = await self.wolves_dialog.get_winner()
        if victim_emo is False:
            # no victim
            await self.next()
            return
        self.wolves_victim = self.wolves_preys[victim_emo]
        self.kill(self.wolves_victim)
        await self.next()

    async def play_wolves_death(self):
        # don't send everything at once for more suspens :)
        await self.main_chan.send("Le village se réveille!")
        if self.wolves_victim is None:
            await self.main_chan.send("Bonne nouvelle, les loups n'ont fait aucune victime cette nuit!")
            await self.next()
            return
        await self.main_chan.send(
            "Cette nuit, {} a été dévoré par les loups :(".format(
                self.wolves_victim.user.mention))
        if self.witch_saved:
            await self.main_chan.send(
                "Heureusement, la sorcière l'a ressuscité!")
            self.witch_saved = False
        else:
            await self.main_chan.send(
                "{} était... {}".format(
                    self.wolves_victim.user.mention, 
                    self.wolves_victim.ROLE_NAME))
            self.process_deaths = True
        self.wolves_victim = None
        await self.next()

    async def play_witch_death(self):
        if self.witch_victim is None:
            await self.next()
            return
        await self.main_chan.send("Mais ce n'est pas tout...")
        await self.main_chan.send(
            "{} a été empoisonné par la sorcière.".format(
                self.witch_victim.user.mention))
        if isinstance(self.witch_victim, Wolf):
            await self.main_chan.send(
                "Vous pouvez remercier la sorcière car {} était un méchant loup-garou!".format(
                    self.witch_victim.user.mention))
        else:
            await self.main_chan.send(
                "Malheureusement, {} était un pauvre {} :'(".format(
                    self.witch_victim.user.mention,
                    self.witch_victim.ROLE_NAME))
        self.process_deaths = True
        self.witch_victim = None
        await self.next()

    async def play_vote(self):
        txt = (
            "Il est temps de voter. Qui voulez-vous éliminer aujourd'hui?\n"
            "{status}\n"
            "{choices}"
        )
        self.vote_candidates = utils.emoji_dict(
            [v for v in self.villagers if v.alive])
        self.vote_dialog = ReactDialog(
            self.main_chan, self.bot, choices=self.vote_candidates, 
            title="Vote", desc=txt)
        await self.vote_dialog.start()
        self.update_vote.start()

    @tasks.loop(seconds=1)
    async def update_vote(self):
        if not await self.vote_dialog.update():
            return
        # Vote has ended
        self.update_vote.stop()
        # winner lol that's dark
        winner_emo = await self.vote_dialog.get_winner()
        if winner_emo is False:
            # no winner = no mayor
            await self.main_chan.send("Personne n'a été éliminé...")
            await self.next()
            return
        winner = self.vote_candidates[winner_emo]
        self.kill(winner)
        await self.main_chan.send("Les villageois ont voté...\n{} a été éliminé!".format(
            winner.user.mention))
        if isinstance(winner, Wolf):
            await self.main_chan.send(
                "Bonne nouvelle, {} était un méchant loup-garou!".format(
                    winner.user.mention))
        else:
            await self.main_chan.send(
                "Malheureusement, {} était un pauvre {} :'(".format(
                    winner.user.mention,
                    winner.ROLE_NAME))
        self.process_deaths = True
        await self.next()

    async def end_turn(self):
        # first check if the game is finished:
        # if all wolves are dead
        if not self.wolves or reduce(lambda x, y: x and not y.alive, self.wolves, True):
            await self.end_game(self.VILLAGERS_WIN)
            return
        # if everyone is dead except wolves
        if not self.villagers or reduce(lambda x, y: x and (not y.alive or isinstance(y, Wolf)), self.villagers, True):
            await self.end_game(self.WOLVES_WIN)
            return
        # if every non-lover is dead and both lovers are alive
        if (self.lovers and len(self.lovers) == 2
          and reduce(lambda x, y: x and (not y.alive or y.lover is not None), True) 
          and reduce(lambda x, y: x and y.alive, self.lovers), True):
            await self.end_game(self.LOVERS_WIN)
            return

        await self.main_chan.send("C'est la nuit, les villageois se rendorment!")
        self.turn += 1
        await self.next()

    VILLAGERS_WIN = 0
    WOLVES_WIN = 1
    LOVERS_WIN = 2

    async def end_game(self, how):
        if how == self.VILLAGERS_WIN:
            result = "Tous les loups sont morts! Les villageois peuvent désormais dormir tranquilles... Bravo!"
            winners = '\n'.join([v.user.mention + ('(mort)' if not v.alive else '') for v in self.villagers if not isinstance(v, Wolf)])
        elif how == self.WOLVES_WIN:
            result = "Tous les villageois sont morts! Les loups ont gagné... Bravo!"
            winners = '\n'.join([v.user.mention + ('(mort)' if not v.alive else '') for v in self.wolves])
        elif how == self.LOVERS_WIN:
            result = "Tout le monde est mort sauf nos deux amoureux. Ils pourront vivre heureux et avoir beaucoup d'enfants mi-loup mi-humain! Trop mignon <3"
            winners = '\n'.join([v.user.mention for v in self.lovers])
        txt = "{result}\n\n**Gagnants:**\n{winners}".format(
            result=result, winners=winners)
        embed = Embed(title="Fin de la partie", type="rich", 
            description=txt)
        utils.set_embed_footer(embed)
        await self.main_chan.send(embed=embed)

        # todo: delete channels after a period of time.
