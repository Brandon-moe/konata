import os
import discord
from discord.ext import commands
from utils import pull_airing_data
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
activity = discord.Game(name="c!help")
client = commands.Bot(command_prefix='c!', activity=activity, help_command=None)

@client.event
async def on_ready():
    print(
        f'{client.user} has connected.:\n'
    )

@client.command()
@commands.has_permissions(administrator=True)
async def postseasonallist(ctx):
    await ctx.send("Generating list of shows, one moment...")
    list = pull_airing_data()
    for format in list:
        await ctx.send("**__{0}__**".format(format))
        for show in list[format]:
            name = show["data"]["Media"]["title"]["romaji"]
            await ctx.send(name)
        await ctx.send("** **")

@client.command()
@commands.has_permissions(administrator=True)
async def deletelist(ctx):
    channel = client.get_channel(ctx.channel.id)
    async for message in channel.history(limit=200):
        if message.author == client.user:
            await message.delete()

@client.command()
@commands.has_permissions(administrator=True)
async def help(ctx):
    embedVar = discord.Embed(title="Help", color=0xA020F0)

    embedVar.add_field(name="help",
    value='''Displays this message.''',
    inline=False)

    embedVar.add_field(name="postseasonallist",
    value='''Posts a list of all shows from the current season.''',
    inline=False)

    embedVar.add_field(name="deletelist",
    value='''Deletes all the posts the bot has made in the current channel.''',
    inline=False)
    await ctx.send(embed = embedVar)

if __name__ == "__main__":
    client.run(TOKEN)
