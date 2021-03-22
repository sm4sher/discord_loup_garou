from discord.ext import tasks

import utils
from react_dialog import ReactDialog
from villager import Villager


class Witch(Villager):
    ROLE_NAME = "Sorcière 🧙‍♀️"
    EMOJI_SAVE = '✔️'
    EMOJI_KILL = '❌'
    EMOJI_DO_NOTHING = '🤷'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.life_power = True
        self.death_power = True

    def get_actions(self):
        # string: ugly and might be annoying for translations?
        choices = dict()
        s = "Voulez vous "
        if self.life_power and self.game.wolves_victim:
            choices[self.EMOJI_SAVE] = "Sauver"
            s += "le sauver"
            if self.death_power:
                s += ", "
        if self.death_power:
            choices[self.EMOJI_KILL] = "Tuer"
            s += "tuer quelqu'un d'autre"
        choices[self.EMOJI_DO_NOTHING] = "Ne rien faire"
        s += " ou ne rien faire?"
        return s, choices

    async def play(self):
        if not self.life_power and not self.death_power:
            # Can't do anything
            await self.game.next()
            return
        await self.game.main_chan.send("La sorcière se réveille!")
        if self.game.wolves_victim is not None:
            victim = "{} a été tué par les loups cette nuit :(".format(
                self.game.wolves_victim.user.mention)
        else:
            victim = "Il n'y a pas eu de victime cette nuit"
        actions, choices = self.get_actions()
        txt = (
            "{victim}\n"
            "{actions}\n"
            "{{status}}\n"
            "{{choices}}"
        ).format(victim=victim, actions=actions)
        self.decision_dialog = ReactDialog(
            self.channel, self.game.bot, choices=choices, 
            title="Sorcière", desc=txt, voters=[self.user])
        await self.decision_dialog.start()
        self.update_decision_dialog.start()

    @tasks.loop(seconds=1)
    async def update_decision_dialog(self):
        if not await self.decision_dialog.update():
            return
        self.update_decision_dialog.stop()
        decision_emo = await self.decision_dialog.get_winner()
        if decision_emo is False or decision_emo == self.EMOJI_DO_NOTHING:
            # do nothing
            await self.game.next()
        elif decision_emo == self.EMOJI_KILL:
            await self.send_kill_dialog()
        elif decision_emo == self.EMOJI_SAVE:
            self.game.witch_saved = True
            self.game.dying.remove(self.game.wolves_victim)
            self.life_power = False
            await self.game.next()

    async def send_kill_dialog(self):
        txt = (
            "Qui voulez-vous empoisonner?\n"
            "{status}\n"
            "{choices}"
        )
        self.victims = utils.emoji_dict(self.game.get_alives(exclude=[self]))
        self.kill_dialog = ReactDialog(
            self.channel, self.game.bot, choices=self.victims, 
            title="Empoisonner", desc=txt, voters=[self.user])
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
            await self.game.next()
            return
        self.game.witch_victim = self.victims[victim_emo]
        self.game.kill(self.game.witch_victim)
        self.death_power = False
        await self.game.next()