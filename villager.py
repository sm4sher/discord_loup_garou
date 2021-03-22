from discord.ext import tasks

import utils
from react_dialog import ReactDialog


class Villager:
    ROLE_NAME = "Simple Villageois 🤷"

    def __init__(self, user, game):
        self.alive = True
        self.user = user
        self.game = game
        self.is_mayor = False
        self.lover = None
        self.channel = None # created later

    def __str__(self):
        return self.user.mention

    async def play(self):
        raise Exception("Not implemented/abstract")

    async def hunter_death(self):
        # overrided in Hunter class
        await self.game.next()

    async def lover_death(self):
        if self.lover is None or not self.lover.alive:
            await self.game.next()
            return
        await self.game.main_chan.send(
            "{dead} et {lover} étaient amoureux... {lover} est incosolable et meurt de chagrin :'(".format(
                dead=self.user.mention,
                lover=self.lover.user.mention))
        await self.game.main_chan.send(
            "{mention} était... {role}".format(
                mention=self.lover.user.mention,
                role=self.lover.ROLE_NAME))
        self.game.kill(self.lover)
        await self.game.next()

    async def mayor_death(self):
        if not self.is_mayor:
            await self.game.next()
            return
        await self.game.main_chan.send(
            "{} est maire. Avant de rendre son dernier souffle, il désigne son successeur.".format(
                self.user.mention))
        txt = (
            "Qui sera le prochain maire?\n"
            "{status}\n"
            "{choices}"
        )
        self.mayor_choices = utils.emoji_dict(self.game.get_alives(exclude=[self]))
        self.mayor_dialog = ReactDialog(
            self.channel, self.game.bot, choices=self.mayor_choices, 
            title="Maire", desc=txt, voters=[self.user])
        await self.mayor_dialog.start()
        self.update_mayor_dialog.start()

    @tasks.loop(seconds=1)
    async def update_mayor_dialog(self):
        if not await self.mayor_dialog.update():
            return
        self.update_mayor_dialog.stop()
        choice_emo = await self.mayor_dialog.get_winner()
        if choice_emo is False:
            await self.game.main_chan.send("Aucun maire n'a été choisi.")
            await self.game.next()
            return
        choice = self.mayor_choices[choice_emo]
        await self.game.main_chan.send(
            "{} est le nouveau maire. Bravo!".format(
                choice.user.mention))
        choice.is_mayor = True
        self.game.mayor = choice
        await self.game.next()

    async def send_card(self):
        await self.channel.send('Vous êtes {}. Bonne chance!'.format(
            self.ROLE_NAME))