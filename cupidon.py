from villager import Villager

class Cupidon(Villager):
    ROLE_NAME = "Cupidon 🏹"
    
    async def play(self):
        # todo
        await self.game.next()