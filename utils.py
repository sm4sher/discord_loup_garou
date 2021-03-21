
def set_embed_footer(embed):
    """ Add a consistent footer to an embed """
    embed.set_footer(text="Loup Garou")


# we need at least 24 for now (elections with max nb of players)
# so there are 11 numbers... then idk
EMOJI_LIST = [
    '0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟',
    '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪', 
    '🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '🟫', '⬛', '⬜'
]
def emoji_dict(l):
    """ Transforms a list into a {emoji: item} dict """
    if len(l) > len(EMOJI_LIST):
        raise Exception("Not implemnted, needs more emojis")
    if len(l) < 11:
        # start at 1 instead of 0 if we can
        emojis = EMOJI_LIST[1:]
    return {emojis[i]: v for i, v in enumerate(l)}