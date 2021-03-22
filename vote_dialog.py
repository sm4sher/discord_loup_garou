from react_dialog import ReactDialog

class VoteDialog(ReactDialog):
    async def get_winner(self, fetch_answers=True, mayor=None):
        if not mayor:
            return await super().get_winner(), False
        if fetch_answers:
            await self.fetch_answers()

        emojis = {e: 0 for e in self.choices}
        may_emo = None
        for u, e in self.voters.items():
            if u is mayor:
                emojis[e] += 2
                may_emo = e
            else:
                emojis[e] += 1
        winners = [e for e, count in emojis.items() if count == emojis[max(emojis, key=emojis.get)]]
        print(winners)
        if not winners:
            return False, False
        if len(winners) == 1:
            return winners[0], False
        return may_emo, True
