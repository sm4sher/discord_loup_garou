from react_dialog import ReactDialog


class StartDialog(ReactDialog):
    EMBED_TITLE = 'Nouvelle partie'
    EMBED_DESC = (
        '{game_starter} a lancé une partie!\n'
        'Cliquez sur le loup pour participer\n'
        'Joueurs: **{nb_players}/{nb_players_min}**\n'
        '{status}'
    )
    CHOICES = ['🐺']
    TIME_LIMIT = 500
    COUNTDOWN_LENGTH = 10

    def __init__(self, game_starter, min_players, *args, **kwargs):
        super().__init__(*args, **kwargs, multivote=True)
        self.game_starter = game_starter
        self.min_players = min_players

        self.countdown = None

    async def update(self, *args, **kwargs):
        # get updated players count
        await self.fetch_answers()
        if self.get_players_nb() >= self.min_players:
            if self.countdown is None:
                self.countdown = self.COUNTDOWN_LENGTH
            else:
                # WARNING this assumes it's updated every sec
                self.countdown -= 1
        else:
            self.countdown = None
        return await super().update(fetch_answers=False)

    def is_ended(self):
        if self.countdown is not None and self.countdown <= 0:
            return True
        return super().is_ended()

    def get_embed_desc(self):
        return self.EMBED_DESC.format(
            game_starter=self.game_starter.mention,
            nb_players=self.get_players_nb(),
            nb_players_min=self.min_players,
            status=self.get_status())

    def get_status(self):
        if self.countdown is None:
            if self.get_remaining_seconds() <= 0:
                return "Partie annulée"
            # Not enough players
            return "En attente d'autres joueurs"
        if self.countdown > 0:
            # Enough players, game is about to start
            return "Début dans {} secondes".format(self.countdown)
        return "Partie lancée"

    def get_players_nb(self):
        try:
            return self.reactions[self.CHOICES[0]]
        except KeyError:
            return 0

    async def get_players(self, fetch_answers=True):
        if fetch_answers:
            await self.fetch_answers(fetch_users=True)
        return [u for u, e in self.voters.items() if e == self.CHOICES[0]]