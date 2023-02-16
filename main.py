import os
import discord
from discord.ext import commands
from utils import pull_airing_data, anilist
from utils.db.db import *
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
activity = discord.Game(name="c!help")
client = commands.Bot(command_prefix='c!', activity=activity, help_command=None)
bot_name = "konata"


@client.event
async def on_ready():
    for guild in client.guilds:
        query = f'''CREATE TABLE IF NOT EXISTS ROLES{guild.id} (
        role_id integer PRIMARY KEY,
        anilist_id integer NOT NULL,
        owner_id integer NOT NULL,
        schedule datetime
        )'''
        execute(query)
        query = f'''CREATE TABLE IF NOT EXISTS CONFIG{guild.id} (
        createchannels bit DEFAULT 0
        )'''
        execute(query)
        query = f'''SELECT * FROM ROLES{guild.id};'''
    print(
        f'{bot_name} has logged on.:\n'
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
    async for message in channel.history(limit=1000):
        if message.author == client.user:
            await message.delete()

@client.command()
async def help(ctx):
    embedVar = discord.Embed(title="Available Commands", color=0xA020F0)

    embedVar.add_field(name="help",
    value='''Displays this message''',
    inline=False)

    embedVar.add_field(name="postseasonallist",
    value='''Posts a list of all shows from the current season''',
    inline=False)

    embedVar.add_field(name="deletelist",
    value='''Deletes all the posts the bot has made in the current channel''',
    inline=False)

    embedVar.add_field(name="createrole",
    value='''Arguments: anime name\nCreate a Discord Role for the given anime''',
    inline=False)

    embedVar.add_field(name="deleterole",
    value='''Arguments: (optional) anime name\nDelete a Discord role for the given anime''',
    inline=False)

    embedVar.add_field(name="assignrole",
    value='''Arguments: (optional) anime name\nGive yourself a Discord role for the given anime''',
    inline=False)

    embedVar.add_field(name="removerole",
    value='''Arguments: (optional) anime name\nRemove yourself from a Discord role for the given anime''',
    inline=False)

    embedVar.add_field(name="viewroles",
    value='''View a list of available roles''',
    inline=False)
    await ctx.send(embed = embedVar)

#Creates a new discord role
@client.command()
@commands.has_permissions(administrator=True)
async def createrole(ctx,arg):
    #searches AniList to find best matches for show name provided
    show_list = list(filter(lambda x: not x["title"]==None, anilist.search_results(arg)))
    #Prompt user to pick a show from the list
    show_embed = discord.Embed(title=f"Pick a show from this list (1-{len(show_list)})",color=0xA020F0)
    for idx,elem in enumerate(show_list):
        show_embed.add_field(name=f'{idx+1}. {elem["title"]}',value=f'{elem["format"]} - {elem["year"]} - {elem["episodes"]} episode'+('' if int(elem["episodes"])==1 else 's'),inline=False)
    show_embed.add_field(name="0. Cancel",value="Cancel creating a new role.")
    menu = await ctx.send(embed = show_embed)
    def check(m):
        return int(m.content) in range(0,len(show_list)+1) and m.channel == ctx.channel and m.author == ctx.author
    msg = await client.wait_for("message",check=check)
    #cleanup chat
    await menu.delete()
    await msg.delete()
    #user cancelled the command
    if msg.content == "0":
        return
    guild = ctx.guild
    #check if role for show already exists
    new_role = show_list[int(msg.content)-1]["title"]
    role_exists = discord.utils.get(guild.roles,name=bot_name+"."+new_role)
    if role_exists:
        await ctx.send(f"『{new_role}』role already exists.")
    else:
        #prefix new role with bot name. to easily distinguish bot created roles from other roles
        await guild.create_role(name=bot_name+"."+new_role)
        await ctx.send(f'『{new_role}』role created')
        #check if you want to make a channel for it
        await ctx.send(f'Would you like to create a new channel for {new_role}? (Y/N)')
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        confirm = await client.wait_for("message",check=check)
        if confirm.content.lower() == "y":
            #create new channel
            await guild.create_text_channel(new_role)
            #set perms (visibility to role only)
            new_channel = guild.channels[-1]
            everyone = [x for x in guild.roles if x.name == "@everyone"][0]
            await new_channel.set_permissions(everyone,view_channel=False)
            role = [x for x in guild.roles if  x.name==bot_name+"."+new_role][0]
            await new_channel.set_permissions(role,view_channel=True)
        #add new role to guild's table in db
        query = f'''INSERT INTO ROLES{guild.id} (role_id,anilist_id,owner_id)
        VALUES (
        {discord.utils.get(guild.roles,name=bot_name+"."+new_role).id},
        {show_list[int(msg.content)-1]["id"]},
        {msg.author.id}
        )'''
        execute(query)
        commit()

@client.command()
@commands.has_permissions(administrator=True)
async def deleterole(ctx,*arg):
    arg = " ".join(arg)
    guild = ctx.guild
    rolelist = [r for r in guild.roles if bot_name in r.name]
    if arg:
        #strip non ascii-characters from argument. Makes it easier for user to type a role they want if it has special characters.
        ascii_reduced_arg = ''.join([i.lower() if ord(i) < 128 else '' for i in arg])
        available_roles = [str(r.name)[len(bot_name)+1:] for r in rolelist]
        ascii_reduced_roles = [''.join([i.lower() if ord(i)<128 else '' for i in text]) for text in available_roles]
        removed_role = [x for x in ascii_reduced_roles if ascii_reduced_arg in x]
        rolelist = [r for r in rolelist if ''.join([i.lower() if ord(i)<128 else '' for i in r.name[len(bot_name)+1:]]) in removed_role]
        if len(removed_role) == 0:
            await ctx.send(f'Could not find role for {arg}. Check your spelling, or create a role with the createrole command.')
            return
        elif len(removed_role) == 1:
            confirm = await ctx.send(f"Are you sure you want to delete the role {rolelist[0].name[len(bot_name)+1:]} from  the server? (Y/N)")
            def check(m):
                return m.channel == ctx.channel and m.author == ctx.author
            confirm = await client.wait_for("message",check=check)
            if confirm.content.lower() == "y":
                await rolelist[0].delete()
                await ctx.send(f"The role {rolelist[0].name[len(bot_name)+1:]} has been deleted.")
            return
        else:
            title = f"Pick a role from this list (1-{len(removed_role)})"
            choice = await embed_menu_selection(title,removed_role,ctx)
            removed_role = rolelist[int(choice)-1]
            confirm = await ctx.send(f"Are you sure you want to delete the role {removed_role.name[len(bot_name)+1:]} from  the server? (Y/N)")
            def check(m):
                return m.channel == ctx.channel and m.author == ctx.author
            confirm = await client.wait_for("message",check=check)
            if confirm.content.lower() == "y":
                await removed_role.delete()
                await ctx.send(f"The role {removed_role.name[len(bot_name)+1:]} has been deleted.")
            return
    #create an embed menu to pick a role if no args given.
    else:
        rolelist = [r for r in guild.roles if bot_name in r.name]
        roles = [r.name[len(bot_name)+1:] for r in rolelist]
        title = f"Pick a role from this list (1-{len(roles)})"
        choice = await embed_menu_selection(title,roles,ctx)
        deleted_role = rolelist[int(choice)-1]
        confirm = await ctx.send(f"Are you sure you want to delete the role {deleted_role.name[len(bot_name)+1:]} from  the server? (Y/N)")
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        confirm = await client.wait_for("message",check=check)
        print(confirm.content)
        if confirm.content.lower() == "y":
            await deleted_role.delete()
            await ctx.send(f"The role {deleted_role.name[len(bot_name)+1:]} has been deleted.")




@client.command()
async def assignrole(ctx,*arg):
    arg = " ".join(arg)
    guild = ctx.guild
    rolelist = [r for r in guild.roles if bot_name in r.name and not r in ctx.message.author.roles]
    if arg:
        #strip non ascii-characters from argument. Makes it easier for user to type a role they want if it has special characters.
        ascii_reduced_arg = ''.join([i.lower() if ord(i) < 128 else '' for i in arg])
        available_roles = [str(r.name)[len(bot_name)+1:] for r in rolelist]
        ascii_reduced_roles = [''.join([i.lower() if ord(i)<128 else '' for i in text]) for text in available_roles]
        removed_role = [x for x in ascii_reduced_roles if ascii_reduced_arg in x]
        rolelist = [r for r in rolelist if ''.join([i.lower() if ord(i)<128 else '' for i in r.name[len(bot_name)+1:]]) in removed_role]
        if len(removed_role) == 0:
            await ctx.send(f'Could not find role for {arg}. Check your spelling, or create a role with the createrole command.')
            return
        elif len(removed_role) == 1:
            await ctx.message.author.add_roles(rolelist[0])
            await ctx.send(f"You have been assigned the {rolelist[0].name[len(bot_name)+1:]} role.")
            return
        else:
            title = f"Pick a role from this list (1-{len(removed_role)})"
            choice = await embed_menu_selection(title,removed_role,ctx)
            removed_role = rolelist[int(choice)-1]
            await ctx.message.author.add_roles(removed_role)
            await ctx.send(f"You have been assigned the {removed_role.name[len(bot_name)+1:]} role.")
    #create an embed menu to pick a role if no args given.
    else:
        rolelist = [r for r in guild.roles if bot_name in r.name and r not in ctx.message.author.roles]
        roles = [r.name[len(bot_name)+1:] for r in rolelist]
        if len(roles) == 0:
            await ctx.send("You already have all available bot roles.")
            return
        title = f"Pick a role from this list (1-{len(roles)})"
        choice = await embed_menu_selection(title,roles,ctx)
        added_role = rolelist[int(choice)-1]
        await ctx.message.author.add_roles(added_role)
        await ctx.send(f"You have been assigned the {added_role.name[len(bot_name)+1:]} role.")

@client.command()
async def removerole(ctx,*arg):
    arg = " ".join(arg)
    guild = ctx.guild
    rolelist = [r for r in ctx.message.author.roles if bot_name in r.name]
    if arg:
        #strip non ascii-characters from argument. Makes it easier for user to type a role they want if it has special characters.
        ascii_reduced_arg = ''.join([i.lower() if ord(i) < 128 else '' for i in arg])
        available_roles = [str(r.name)[len(bot_name)+1:] for r in rolelist]
        ascii_reduced_roles = [''.join([i.lower() if ord(i)<128 else '' for i in text]) for text in available_roles]
        removed_role = [x for x in ascii_reduced_roles if ascii_reduced_arg in x]
        rolelist = [r for r in rolelist if ''.join([i.lower() if ord(i)<128 else '' for i in r.name[len(bot_name)+1:]]) in removed_role]
        if len(removed_role) == 0:
            all_roles = [x.name for x in guild.roles if bot_name in x.name]
            for elem in all_roles:
                if ascii_reduced_arg in ''.join([i.lower() if ord(i)<128 else '' for i in elem[len(bot_name)+1:]]):
                    await ctx.send(f'You do not currently have the {elem[len(bot_name)+1:]} role.')
                    return
            await ctx.send(f'Could not find role for {arg}. Check your spelling, or create a role with the createrole command.')
            return
        elif len(removed_role) == 1:
            await ctx.message.author.remove_roles(rolelist[0])
            await ctx.send(f"You have been removed from the {rolelist[0].name[len(bot_name)+1:]} role.")
            return
        else:
            title = f"Pick a role from this list (1-{len(removed_role)})"
            choice = await embed_menu_selection(title,removed_role,ctx)
            removed_role = rolelist[int(choice)-1]
            await ctx.message.author.remove_roles(removed_role)
            await ctx.send(f"You have been removed from the {removed_role.name[len(bot_name)+1:]} role.")
    else:
         if len(rolelist) == 0:
             await ctx.send(f"You currently do not have any bot assigned roles")
             return
         roles = [r.name[len(bot_name)+1:] for r in rolelist]
         title = f"Pick a role from this list (1-{len(roles)})"
         choice = await embed_menu_selection(title,roles,ctx)
         removed_role = rolelist[int(choice)-1]
         await ctx.message.author.remove_roles(removed_role)
         await ctx.send(f"You have been removed from the {removed_role.name[len(bot_name)+1:]} role.")


async def embed_menu_selection(title,list,ctx):
    embed = discord.Embed(title=title,color=0xA020F0)
    for idx,elem in enumerate(list):
        embed.add_field(name=f'',value=f'{idx+1}. {elem}',inline=False)
    embed.add_field(name="",value="0. Cancel",inline=False)
    menu = await ctx.send(embed = embed)
    def check(m):
        return int(m.content) in range(0,len(list)+1) and m.channel == ctx.channel and m.author == ctx.author
    msg = await client.wait_for("message",check=check)
    #cleanup chat
    await menu.delete()
    await msg.delete()
    #user cancelled the command
    if msg.content == "0":
        return
    return msg.content

@client.command()
async def viewroles(ctx):
    guild = ctx.guild
    roles = guild.roles
    #get list of roles
    available_roles = [str(r.name)[len(bot_name)+1:] for r in roles if bot_name in r.name]
    #display roles in an embedded block
    embedVar = discord.Embed(title="Available Roles", color=0xA020F0)
    for role in available_roles:
        embedVar.add_field(name="",
        value=role,
        inline=False)
    await ctx.send(embed = embedVar)
if __name__ == "__main__":
    client.run(TOKEN)
