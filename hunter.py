from discord.ext import tasks

import utils
from react_dialog import ReactDialog
from villager import Villager


class Hunter(Villager):
    ROLE_NAME = "Chasseur 🔫"

    async def hunter_death(self):
        self.victims = utils.emoji_dict(self.game.get_alives(exclude=[self]))
        if not self.victims:
            await self.game.next()
            return
        self.game.main_chan.send(
            "{} est un chasseur! Il ne va pas mourir sans se battre!.".format(
                self.user.mention))
        txt = (
            "Qui voulez-vous tuer avant de mourir?\n"
            "{status}\n"
            "{choices}"
        )
        self.kill_dialog = ReactDialog(
            self.channel, self.game.bot, choices=self.victims, 
            title="Tuer", desc=txt, voters=[self.user])
        await self.kill_dialog.start()
        self.update_kill_dialog.start()

    @tasks.loop(seconds=1)
    async def update_kill_dialog(self):
        if not await self.kill_dialog.update():
            return
        self.update_kill_dialog.stop()
        victim_emo = await self.kill_dialog.get_winner()
        if victim_emo is False:
            # no victim
            self.game.main_chan.send(
                "Le chasseur est finalement mort sans tuer personne...")
            await self.game.next()
            return
        victim = self.victims[victim_emo]
        self.game.kill(victim)
        await self.game.main_chan.send(
            "{mention} a le temps d'armer son fusil et de tirer sur {victim}. Puis il s'écroule par terre et meurt...".format(
                mention=self.user.mention,
                victim=victim.muser.mention))
        await self.game.next()