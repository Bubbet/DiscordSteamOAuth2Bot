from sqlite3 import connect
from datetime import datetime


class SqlInterface():
    def __init__(self):
        create_users_table = '''CREATE TABLE IF NOT EXISTS `Users` (
                        `DiscordID`	NTEGER UNIQUE,
                        `SteamID` INTEGER UNIQUE,
                        `DiscordName` TEXT,
                        `SteamName`	TEXT,
                        `AddDate` TEXT,
                        PRIMARY KEY(`DiscordID`,`SteamID`)
                    );'''
        create_rank_connections = '''CREATE TABLE IF NOT EXISTS `RankConnections` (
            `GuildID` INTEGER,
            `RoleID` INTEGER UNIQUE,
            `RankName` TEXT,
            PRIMARY KEY(`RoleID`)
        );'''
        create_rcon_table = '''CREATE TABLE IF NOT EXISTS `RconList` (
            `GuildID` INTEGER,
            `IPAddress` TEXT,
            `Port` INTEGER,
            `Password` TEXT,
            `NickName` TEXT
        );'''
        create_channel_table = '''CREATE TABLE IF NOT EXISTS `GuildChannels` (
            `GuildID` INTEGER UNIQUE,
            `ChannelID` INTEGER
        );'''
        self.sql = connect('db.db')
        self.sql.execute(create_users_table)
        self.sql.execute(create_rank_connections)
        self.sql.execute(create_rcon_table)
        self.sql.execute(create_channel_table)
        self.sql.commit()
        self.sql.close()

    def adduser(self, steam, user):
        select_statement = 'SELECT DiscordID FROM Users WHERE DiscordID = ?'
        insert_statement = 'INSERT INTO Users VALUES (?,?,?,?,?)'
        with connect('db.db') as sql:
            if not sql.execute(select_statement, (user["id"],)).fetchone():
                sql.execute(insert_statement, [user["id"], steam["id"], f'{user["username"]}#{user["discriminator"]}', steam["name"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    def assignrole(self, guild_id, discord_role, ranks_rank):
        insert_statement = "INSERT INTO RankConnections VALUES (?,?,?)"
        with connect('db.db') as sql:
            sql.execute(insert_statement, [guild_id, discord_role, ranks_rank])

    def addrcon(self, guild_id, ip_address, port, password, nickname=None):
        insert_statement = "INSERT INTO RconList VALUES (?,?,?,?,?)"
        with connect('db.db') as sql:
            sql.execute(insert_statement, [guild_id, ip_address, port, password, nickname])

    def removercon(self, guild_id, ip_address):
        delete_statement = "DELETE FROM RconList WHERE (GuildID=? AND IPAddress=?)"
        with connect('db.db') as sql:
            sql.execute(delete_statement, [guild_id, ip_address])

    def listrcons(self, guild_id):
        with connect('db.db') as sql:
            return sql.execute("SELECT IPAddress, Port, Password, NickName FROM RconList WHERE GuildID=?", [guild_id]).fetchall()

    def get_rank_from_role(self, role_id):
        with connect('db.db') as sql:
            que = sql.execute("SELECT RankName FROM RankConnections WHERE RoleID=?", [role_id]).fetchone()
            if que:
                return que[0]
            else:
                return False

    def get_steam_from_disord(self, member_id):
        with connect('db.db') as sql:
            que = sql.execute("SELECT SteamID FROM Users WHERE DiscordID=?", [member_id]).fetchone()
            if que:
                return que[0]
            else:
                return False

    def get_nickname(self, guild_id, host, port):
        get_statement = "SELECT NickName FROM RconList WHERE (GuildID=? AND IPAddress=? AND Port=?)"
        with connect('db.db') as sql:
            que = sql.execute(get_statement, [guild_id, host, port]).fetchone()
            if que and que[0] is not None:
                return que[0]
            else:
                return f"{host}:{port}"

    def set_default_channel(self, guild_id, channel_id):
        insert_statement = 'INSERT OR REPLACE INTO GuildChannels VALUES (?,?)'
        with connect('db.db') as sql:
            sql.execute(insert_statement, [guild_id, channel_id])

    def get_default_channel(self, guild_id):
        with connect('db.db') as sql:
            que = sql.execute("SELECT ChannelID FROM GuildChannels WHERE GuildID=?", [guild_id]).fetchone()
            if que:
                return que[0]
            else:
                return False

# test = SqlInterface()
# test.addrcon(282371226049970176, '127.0.0.1', 27015, 'weed')
# print(test.listrcons(282371226049970176))
