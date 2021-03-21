from villager import Villager


class Thief(Villager):
    ROLE_NAME = "Voleur 💰"
    
    async def play(self):
        # todo
        await self.game.next()