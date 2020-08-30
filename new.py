from classes.settingsinterface import Settings
from classes.sqlinterface import SqlInterface
from classes.discordbot import DiscordBot
from classes.flaskserver import FlaskServer

settings = Settings()
sql = SqlInterface()

discordbot = DiscordBot(settings, sql)
flaskserver = FlaskServer(__name__, settings, sql, discordbot)
