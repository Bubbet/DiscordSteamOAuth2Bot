from threading import Thread
from discord.ext import commands
from classes.rconinterface import RconInterface
# Look in to splitting command groups into cogs


class DiscordBot(Thread):
    def __init__(self, settings, sql):
        Thread.__init__(self)
        self.bot = commands.Bot(command_prefix="!")
        self.settings = settings
        self.sql = sql

        @self.bot.command(name="refresh", aliases=["refreshranks"])
        async def refresh_ranks(ctx):
            """Used to update your ranks in-game.
            Use this command then reconnect to the Avorion server.
            Make sure you've authenticated the OAuth2 first."""
            out = self.add_ranks_from_roles(ctx.author.id, ctx.author.roles)
            if out:
                await ctx.send(out)

        @self.bot.command(name="linksteam")
        async def link_steam(ctx, steam_id):
            """Enter your steam id 64, if you put the wrong id in your ranks won't work.
            You are better off using the OAuth2 web link."""
            entry = {"id": int(steam_id), "name": steam_id}
            user = {"id": ctx.author.id,
                    "username": ctx.author.name,
                    "discriminator": ctx.author.discriminator,
                    "roles": ctx.author.roles}
            self.sql.adduser(entry, user)
            await self.update_user(entry, user)
            await ctx.send(f"Linked Steam Account.")

        @self.bot.command(name="setrole")
        @commands.has_guild_permissions(administrator=True)
        async def set_role(ctx, discord_role=None, ranks_rank=None):
            """Sets the discord role to the ranks rank.
            Usage: Discord_role Exact_rank_name"""
            if not discord_role or not ranks_rank:
                message = "Missing"
                if not discord_role:
                    message += ' discord role'
                if not discord_role and not ranks_rank:
                    message += ' and'
                if not ranks_rank:
                    message += ' ranks rank'
                message += '.'
                return await ctx.send(message)

            for role in ctx.guild.roles:
                if role.name.find(discord_role) >= 0:
                    discord_role = role
                    break

            if discord_role.id:
                self.sql.assignrole(ctx.guild.id, discord_role.id, ranks_rank)
                for member in discord_role.members:
                    self.add_ranks_from_roles(member.id, [discord_role])
                await ctx.send(f"Assigned {discord_role.name} to {ranks_rank}")

        @self.bot.command(name="setchannel")
        @commands.has_guild_permissions(administrator=True)
        async def set_channel(ctx):
            """Sets the current channel to the default information channel for the bot."""
            self.sql.set_default_channel(ctx.guild.id, ctx.channel.id)
            await ctx.send(f"Set default response channel to {ctx.channel.mention}")

        @self.bot.command(name="addrcon")
        @commands.has_guild_permissions(administrator=True)
        async def add_rcon(ctx, ip_address=None, port=None, password=None, nickname=None):
            """Used to add a rcon address to the database.
            Usage: ip_address, port, password, nickname(optional)"""
            await ctx.message.delete()
            if not ip_address or not port or not password:
                message = "Missing"
                if not ip_address:
                    message += " IP address"
                if not ip_address and not port:
                    if not ip_address and not port and not password:
                        message += ","
                    else:
                        message += " and"
                if not port:
                    message += " port"
                if not port and not password:
                    message += " and"
                if not password:
                    message += " password"
                message += "."
                return await ctx.send(message)
            self.sql.addrcon(ctx.guild.id, ip_address, int(port), password, nickname)
            self.guild_rcons[ctx.guild.id].append(RconInterface(ip_address, int(port), password))
            password = r'\*' * len(password)
            await ctx.send(f"Added {ip_address}:{port}, password: **{password}** with nickname {nickname} to rcon list.")

        @self.bot.command(name="removercon")
        @commands.has_guild_permissions(administrator=True)
        async def remove_rcon(ctx, ip_address=None):
            """Removes all rcons with the ip from the database.
            Usage: ip_address"""
            if not ip_address:
                return await ctx.send("Missing IP address.")
            self.sql.removercon(ctx.guild.id, ip_address)
            await ctx.send(f"Removed all mentions of {ip_address} for this guild from database.")

        @self.bot.command(name="listrcons", aliases=["listrcon"])
        @commands.has_guild_permissions(administrator=True)
        async def list_rcons(ctx):
            """Prints the stored rcon servers for this guild."""
            message = "This guild has the following rcon addresses and ports:\n"
            for rcon in self.sql.listrcons(ctx.guild.id):
                message += f"{rcon[0]}:{rcon[1]}, {rcon[3]};\n"
            await ctx.send(message)

        @self.bot.command(name="activercons")
        @commands.has_guild_permissions(administrator=True)
        async def active_rcons(ctx):
            """Prints the running rcon servers for this guild."""
            message = "This guild has the following rcons active:\n"
            for rcon in self.guild_rcons[ctx.guild.id]:
                if rcon.active:
                    message += f"{self.sql.get_nickname(ctx.guild.id, rcon.con.host, rcon.con.port)};\n"
            await ctx.send(message)

        @self.bot.command(name="reconnectrcons")
        @commands.has_guild_permissions(administrator=True)
        async def reconnect_rcons(ctx):
            """Forces a reconnect of the rcon servers for this guild."""
            message = "Attempting the reconnection of these rcons:\n"
            for rcon in self.guild_rcons[ctx.guild.id]:
                if not rcon.getstatus():
                    rcon.reconnect()
                    message += f"{self.sql.get_nickname(ctx.guild.id, rcon.con.host, rcon.con.port)};\n"
            await ctx.send(message)

        @self.bot.command(name="broadcastrcon", aliases=['brcon'])
        @commands.has_guild_permissions(administrator=True)
        async def broadcast_rcons(ctx, *args):
            """Standard rcon command issuing, except it goes to every server attached to the guild."""
            message = "Responses from rcons follow:\n"
            message += self.broadcast(ctx.guild.id, ' '.join(args))
            for text in [message[ind:ind + 2000] for ind in range(0, len(message), 2000)]:
                await ctx.send(text)

        # @add_rcon.error
        @remove_rcon.error
        @list_rcons.error
        @active_rcons.error
        @reconnect_rcons.error
        @broadcast_rcons.error
        async def rcon_error(ctx, err):
            print(err)
            if type(err.original) is ConnectionRefusedError:
                await ctx.send("There is currently no active rcon connections.")
            else:
                await ctx.send(f"{ctx.author.mention} you don't have permission to use rcon.")

        @set_role.error
        async def role_error(ctx, err):
            print(err)
            await ctx.send(f"{ctx.author.mention} you don't have permission to set roles.")

        @self.bot.event
        async def on_member_update(before, after):
            if before.roles == after.roles:
                return

            add_roles, remove_roles = [], []

            for bef in before.roles:
                exists = False
                for aft in after.roles:
                    if bef == aft:
                        exists = True
                if not exists:
                    remove_roles.append(bef)

            for aft in after.roles:
                exists = False
                for bef in before.roles:
                    if bef == aft:
                        exists = True
                if not exists:
                    add_roles.append(aft)

            message = f"User {after.mention} updated with ranks:\n"
            message += self.add_ranks_from_roles(before.id, add_roles)
            message += self.remove_ranks_from_roles(before.id, remove_roles)
            await self.get_default_channel(before.guild.id).send(message)

        @self.bot.event
        async def on_ready():
            self.guild_rcons = {}
            for guild in self.bot.guilds:
                rcons = []
                for info in self.sql.listrcons(guild.id):
                    rcons.append(RconInterface(*info))
                self.guild_rcons[guild.id] = rcons

        self.start()

    def __del__(self):
        self.bot.logout()
        self.bot.close()

    def broadcast(self, guild_id, command):
        message = ""
        for rcon in self.guild_rcons[guild_id]:
            message += f"__{self.sql.get_nickname(guild_id, rcon.con.host, rcon.con.port)}__\n{rcon.command(command)}"
        return message

    async def update_user(self, steam, user):
        """From oauth, contains info sent to sql"""
        did = type(user) is dict and user["id"] or user.id
        for guild in self.bot.guilds:
            self.add_ranks_from_roles(did, guild.get_member(did).roles)

    def add_ranks_from_roles(self, id, roles):
        """List of discord roles, use id to find steamid and give roles"""
        message = "Console results from rank adding:\n"
        for role in roles:
            if role.id == role.guild.id:
                continue
            rank = self.sql.get_rank_from_role(role.id)
            steam_id = self.sql.get_steam_from_disord(id)
            if not rank or not steam_id:
                channel = self.get_default_channel(role.guild.id)
                if channel:
                    self.bot.loop.create_task(channel.send(
                        f"Failed to find rank or id: {rank or role.name + '(Discord)'} {steam_id}"))
                else:
                    print("Failed to find rank or id:", rank, steam_id)
                continue
            message += self.broadcast(role.guild.id, f"/adduser {rank} {steam_id}")
        return message

    def remove_ranks_from_roles(self, id, roles):
        """List of discord roles, use id to find steamid and take roles"""
        message = "Console results from rank removing:\n"
        for role in roles:
            rank = self.sql.get_rank_from_role(role.id)
            steam_id = self.sql.get_steam_from_disord(id)
            if not rank or not steam_id:
                channel = self.get_default_channel(role.guild.id)
                if channel:
                    self.bot.loop.create_task(channel.send(
                        f"Failed to find rank or id: {rank or role.name + '(Discord)'} {steam_id}"))
                else:
                    print("Failed to find rank or id:", rank, steam_id)
                continue
            message += self.broadcast(role.guild.id, f"/removeuser {rank} {steam_id}")
        return message

    def get_default_channel(self, guild_id):
        return self.bot.get_channel(self.sql.get_default_channel(guild_id))

    def run(self):
        self.bot.run(self.settings['discord_bot_token'])