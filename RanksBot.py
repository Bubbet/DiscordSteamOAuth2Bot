import os, sqlite3, json
from pathlib import Path
from datetime import datetime
from threading import Thread
from discord.ext import commands
from flask import Flask, session, redirect, request, url_for, jsonify, Response
from requests_oauthlib import OAuth2Session
from paypal.paypal_create import CreateOrder
from paypal.paypal_capture import CaptureOrder


class Settings:
    def __setitem__(self, key, value):
        self.config[key] = value

    def __getitem__(self, item):
        try:
            return self.config[item]
        except KeyError:
            return None

    def __init__(self):
        try:
            with open('settings.json') as file:
                self.config = json.load(file)
        except IOError:
            self.config = {}
        self.getfromuser()
        self.save()

    def getfromuser(self):
        """List of values used in the script and their description, gathered by the loop."""
        values = {'discord_client_id': 'Discord Client ID',
                  'discord_client_secret': 'Discord Client Secret',
                  'discord_bot_token': 'Discord Bot Token',
                  'paypal_id': 'PayPal ID',
                  'paypal_secret': 'PayPal Secret',
                  'paypal_email': 'PayPal Email',
                  'discord_guild_id': 'Discord server\'s guild ID',
                  'discord_channel_id': 'Discord channel ID in your guild',
                  'callback_redirect': 'Callback Url - Use /addrank if you didn\'t want to use PayPal or blank if you wanted to use the internal page'}
        for key, value in values.items():
            if not self[key]:
                self[key] = input(f'Enter your {value}:')

    def save(self):
        try:
            with open('settings.json', 'w') as file:
                json.dump(self.config, file, indent=2)
        except IOError as e:
            print(f'Error saving config. Exception: {e}')


settings = Settings()
API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'


class Sqlinterface:
    def __init__(self):
        create_users_table = '''CREATE TABLE IF NOT EXISTS `Users` (
                `DiscordID`	INTEGER UNIQUE,
                `SteamID`	INTEGER UNIQUE,
                `DiscordName`	TEXT,
                `SteamName`	TEXT,
                `DonationPackage`	TEXT,
                `DonationDate`	TEXT,
                `DonationOrderID` TEXT,
                PRIMARY KEY(`DiscordID`,`SteamID`)
            );'''
        with sqlite3.connect('users.db') as sql:
            sql.execute(create_users_table)

    def adduser(self, steam, user):
        select_statement = 'SELECT DiscordID FROM Users WHERE DiscordID = ?'
        insert_statement = 'INSERT INTO Users VALUES (?,?,?,?,?,?,?)'
        with sqlite3.connect('users.db') as sql:
            if not sql.execute(select_statement, (user["id"],)).fetchone():
                sql.execute(insert_statement, [
                    user["id"], steam["id"], f'{user["username"]}#{user["discriminator"]}', steam["name"], 'None',
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")], '')

    def getsteamid(self, discordID):
        select_statement = 'SELECT SteamID, SteamName FROM Users WHERE DiscordID = ?'
        with sqlite3.connect('users.db') as sql:
            return sql.execute(select_statement, (discordID,)).fetchone()


class DiscordBot(Thread):
    def __init__(self):
        Thread.__init__(self)
        bot = commands.Bot(command_prefix='!')
        self.bot = bot

        @self.bot.event
        async def on_ready():
            self.guild = bot.guilds[0]
            self.channel = self.guild.get_channel(settings['discord_channel_id'])
            # todo replace with proper method to get channel
            guild_id = settings['discord_guild_id']
            for guild in bot.guilds:
                if guild_id and guild.id == int(guild_id):
                    self.guild = guild
            print(f'{self.bot.user.name} has connected to {self.guild}!')

        @self.bot.command()
        async def adduser(ctx, user=None):
            member = await self.find_member(ctx=ctx, user=user)
            if member:
                await self.add(member.id)

        @self.bot.command()
        async def whois(ctx, user=None, steam=None):
            member = await self.find_member(ctx=ctx, user=user)
            steam = sqlinterface.getsteamid(member.id)
            await ctx.send(f'{member.name}\'s SteamID is {steam[0]} and Steam name at time of OAuth2 is {steam[1]}')

        self.start()

    async def find_member(self, ctx=None, user=''):
        # why i should even have to do this and its not in the api who knows.
        """Finds a member in the guild using partial name or id"""
        if ctx is None:
            ctx = {'guild': self.bot.guild}
        if user is not None:
            if user.startswith('<@!'):
                user = user[len('<@!'):-1]
            try:
                user = int(user)
                user = ctx.guild.get_member(user_id=user)
            except(TypeError, ValueError):
                for member in ctx.guild.members:
                    if member.name.find(user):
                        user = member
                        break
            return user
        else:
            if ctx.author:
                return ctx.author
        return

    async def add(self, id):
        steam = sqlinterface.getsteamid(id)
        user = self.guild.get_member(user_id=int(id))
        await self.channel.send(f'Thank you for donating, {user.name}.')
        await user.create_dm()
        await user.dm_channel.send(
            f'Thank you for donating, {user.name}.'
        )

    def addu(self, id):
        self.bot.loop.create_task(self.add(id))

    def run(self):
        self.bot.run(settings['discord_bot_token'])


try:
    var = os.environ['BOTRUNNING']
    sqlinterface = Sqlinterface()
    discordbot = DiscordBot()
except KeyError:
    os.environ['BOTRUNNING'] = 'True'
app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = settings['discord_client_secret']


def token_updater(token):
    session['oauth2_token'] = token


def make_session(token=None, state=None, scope=None):
    oauth2_redirect_uri = 'http://localhost:5000/' + url_for('.callback')[1:]  # request.url +
    if 'http://' in oauth2_redirect_uri:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    return OAuth2Session(
        client_id=settings['discord_client_id'],
        token=token,
        state=state,
        scope=scope,
        redirect_uri=oauth2_redirect_uri,
        auto_refresh_kwargs={
            'client_id': settings['discord_client_id'],
            'client_secret': settings['discord_client_secret'],
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater)


@app.route("/client_token", methods=["GET"])
def client_token():
    return gateway.client_token.generate()


@app.route('/')
def index():
    scope = request.args.get(
        'scope',
        'connections')
    discord = make_session(scope=scope.split(' '))
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)


@app.route('/callback')
def callback():
    if request.values.get('error'):
        return request.values['error']
    discord = make_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=settings['discord_client_secret'],
        authorization_response=request.url)
    session['oauth2_token'] = token
    user = discord.get(API_BASE_URL + '/users/@me').json()
    connections = discord.get(API_BASE_URL + '/users/@me/connections').json()
    for entry in connections:
        if entry['type'] == 'steam':
            sqlinterface.adduser(entry, user)
    if settings['callback_redirect']:
        return redirect(settings['callback_redirect'])
    else:
        return redirect(url_for('.paypalbutton'))


@app.route('/addrank')
def addrank():
    '''Used when paypal is disabled and CALLBACK_REDIRECT is set to this url'''
    if settings['callback_redirect'] != url_for('.addrank'):
        return '<p>Paypal is Enabled</p>'
    discord = make_session(token=session.get('oauth2_token'))
    user = discord.get(API_BASE_URL + '/users/@me').json()
    discordbot.addu(user['id'])
    return '<p>Added rank!</p>'


# PayPal
@app.route('/create-paypal-transaction', methods=['GET', 'POST'])
def createtransaction():
    order = CreateOrder(settings['paypal_id'], settings['paypal_secret']).create_order(debug=True)
    return jsonify({'orderID': order.result.id})


@app.route('/capture-paypal-transaction/<orderID>')
def capturetransaction(orderID):
    response = CaptureOrder(settings['paypal_id'], settings['paypal_secret']).capture_order(orderID, debug=True)
    if response.status_code == 201:
        discord = make_session(token=session.get('oauth2_token'))
        user = discord.get(API_BASE_URL + '/users/@me').json()
        discordbot.addu(user['id'])
    return Response({'status': response.status_code})


@app.route('/paypalbutton')
def paypalbutton():
    order = '''
            {createOrder: function() {
              return fetch('/create-paypal-transaction', {
                method: 'post',
                headers: {
                  'content-type': 'application/json'
                }
              }).then(function(res) {
                return res.json();
              }).then(function(data) {
                return data.orderID; // Use the same key name for order ID on the client and server
              });
            },
            onApprove: function(data) {
              return fetch('/capture-paypal-transaction/'+data.orderID, {
                headers: {
                  'content-type': 'application/json',
                },
              }).then(function(res) {
                return res.json();
              }).then(function(details) {
                alert('Transaction funds captured from ' + details.payer_given_name);
              })
            }}
        '''
    button = f'''
            <head>
              <meta name="viewport" content="width=device-width, initial-scale=1"> <!-- Ensures optimal rendering on mobile devices. -->
              <meta http-equiv="X-UA-Compatible" content="IE=edge" /> <!-- Optimal Internet Explorer compatibility -->
            </head>

            <body>
                <script
                    src="https://www.paypal.com/sdk/js?client-id={settings['paypal_id']}"> // Required. Replace SB_CLIENT_ID with your sandbox client ID.
                </script>

                <div id="paypal-button-container"></div>

                <script>
                    paypal.Buttons({order}).render('#paypal-button-container');
                </script>
            </body>
        '''
    return button


app.run()
