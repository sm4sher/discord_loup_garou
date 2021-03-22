from discord import Embed

from datetime import datetime
from functools import reduce

import utils

# todo: add optional @here mention
class ReactDialog:
    """ Dialog allowing users to react within a given time 
        choices must be either a list of emoji or a dict {emoji: label}"""
    EMBED_TITLE = "Vote"
    EMBED_DESC = "Vous pouvez voter maintenant.\n{status}\n{choices}"
    CHOICES = {'✔️': "Oui", '❌': "Non"}
    TIME_LIMIT = 10

    def __init__(self, channel, bot, choices=None, title=None, desc=None,
            time_limit=None, voters=None, multivote=False, end_early=True):
        self.channel = channel
        self.bot = bot
        self.choices = choices
        self.title = title
        self.desc = desc
        self.time_limit = time_limit
        self.voters = voters
        self.multivote = multivote

        self.reactions = {}
        if self.voters is not None:
            self.whitelist = True
            self.voters = {u: False for u in self.voters}
        else:
            self.whitelist = False
            self.voters = {}
        # we can't end early if we don't know the voters
        self.end_early = end_early and self.whitelist
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
        if self.ended:
            # easy way to end it before the time limit
            return True
        if self.end_early and reduce(lambda x, y: x and y, self.voters, True):
            # return True if all voters have voted
            return True

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
        # reset reacs & voters bc they could have removed their vote
        self.reactions = {e: 0 for e in self.get_choices()}
        self.voters = {u: False for u in self.voters}
        # if there's a whitelist or multivotes are not allowed, we need users
        if fetch_users or self.whitelist or not self.multivote:
            for r in self.msg.reactions:
                if r.emoji not in self.get_choices():
                    continue
                async for u in r.users():
                    if u.id == self.bot.user.id:
                        continue # it me lel
                    if self.whitelist and u not in self.voters:
                        continue # not allowed to vote
                    if not self.multivote and self.voters.get(u):
                        # omg they voted mutiple time that's not nice :(
                        continue
                    self.reactions[r.emoji] += 1
                    self.voters[u] = r.emoji
        else:
            # easier method to count reactions if we don't need users
            # sub 1 from the count if I reacted (it's possible I haven't yet)
            self.reactions = {
                r.emoji: r.count - (1 if r.me else 0)
                for r in self.msg.reactions
                if r.emoji in self.get_choices()
            }

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