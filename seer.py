from discord.ext import tasks

import utils
from react_dialog import ReactDialog
from villager import Villager


class Seer(Villager):
    ROLE_NAME = "Voyante 🔮"
    
    async def play(self):
        await self.game.main_chan.send("La Voyante se réveille!")
        txt = (
            "De quel joueur voulez-vous sonder la véritable personnalité?\n"
            "{status}\n"
            "{choices}"
        )
        self.choices = utils.emoji_dict(self.game.get_alives(exclude=[self]))
        self.dialog = ReactDialog(
            self.channel, self.game.bot, choices=self.choices, 
            title="Voyante", desc=txt, voters=[self.user])
        await self.dialog.start()
        self.update_dialog.start()

    @tasks.loop(seconds=1)
    async def update_dialog(self):
        if not await self.dialog.update():
            return
        self.update_dialog.stop()
        choice_emo = await self.dialog.get_winner()
        if choice_emo is False:
            await self.game.next()
            return
        choice = self.choices[choice_emo]
        await self.channel.send("{} est {}...".format(
            choice.user.mention, choice.ROLE_NAME))
        await self.game.next()