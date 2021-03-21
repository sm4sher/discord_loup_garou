from discord import Embed

from datetime import datetime

import utils

# todo: add optional @here mention
# todo: end early if all voters are done
# todo: prevent multi votes
class ReactDialog:
    """ Dialog allowing users to react within a given time 
        choices must be either a list of emoji or a dict {emoji: label}"""
    EMBED_TITLE = "Vote"
    EMBED_DESC = "Vous pouvez voter maintenant.\n{status}\n{choices}"
    CHOICES = {'✔️': "Oui", '❌': "Non"}
    TIME_LIMIT = 10

    def __init__(self, channel, bot, choices=None, title=None, desc=None,
            time_limit=None, voters=None):
        self.channel = channel
        self.bot = bot
        self.choices = choices
        self.title = title
        self.desc = desc
        self.time_limit = time_limit
        self.voters = voters

        self.reactions = {}
        self.users = {}
        self.ended = False

    def get_embed_title(self):
        if self.title is not None:
            return self.title
        return self.EMBED_TITLE

    def get_embed_desc(self):
        if self.desc is not None:
            desc = self.desc
        else:
            desc = self.EMBED_DESC
        return desc.format(
            status=self.get_status(), 
            choices=self.format_choices())

    def get_status(self):
        return "Temps restant: {}s".format(self.get_remaining_seconds())

    def get_remaining_seconds(self):
        elapsed = (datetime.now() - self.start_time).seconds 
        return max(0, self.get_time_limit() - elapsed)

    def get_choices(self):
        if self.choices is not None:
            choices = self.choices
        else:
            choices = self.CHOICES
        if isinstance(choices, list):
            choices = {e: "" for e in choices}
        return choices

    def get_time_limit(self):
        if self.time_limit is not None:
            return self.time_limit
        return self.TIME_LIMIT

    def is_ended(self):
        # easy way to end it before the time limit
        if self.ended:
            return True
        #if self.voters is not None:

        self.ended = self.get_remaining_seconds() <= 0
        return self.ended

    async def start(self):
        self.start_time = datetime.now()
        embed = self.build_embed()
        self.msg = await self.channel.send(embed=embed)
        await self.add_reactions()
        
    async def update(self, fetch_answers=False, fetch_users=False):
        """ Update dialog
            fetch_answers will refresh the message to get new reacs
            fetch_users will also fetch who answered what """
        if fetch_answers:
            self.fetch_answers(fetch_users=fetch_users)

        # todo: check if embed changed to avoid useless edits
        embed = self.build_embed()
        await self.msg.edit(embed=embed)

        return self.is_ended()

    async def fetch_answers(self, fetch_users=False):
        # refetch message to get new reactions
        self.msg = await self.channel.fetch_message(self.msg.id)
        # Update answers
        for r in self.msg.reactions:
            if r.emoji not in self.get_choices():
                continue
            # don't count mine but it's possible I haven't reacted yet
            self.reactions[r.emoji] = r.count - (1 if r.me else 0) 
            if fetch_users:
                self.users[r.emoji] = [
                u async for u in r.users() if u.id != self.bot.user.id
            ]

    def format_choices(self):
        choices = self.get_choices()
        return "\n".join(
            ["{} {}".format(e, l) for e, l in choices.items()])

    def build_embed(self):
        title = self.get_embed_title()
        embed = Embed(title=title, type="rich", 
            description=self.get_embed_desc())
        utils.set_embed_footer(embed)
        return embed

    async def add_reactions(self):
        for e in self.get_choices().keys():
            await self.msg.add_reaction(e)

    # some utilities funcs
    async def get_winner(self, fetch_answers=True):
        """ Returns the most reacted emoji """
        if fetch_answers:
            await self.fetch_answers()
        winner = False
        top = 0
        for e, count in self.reactions.items():
            if count > top:
                top = count
                winner = e
            elif count == top:
                # draw = no winner
                winner = False
        return winner