from flask import Flask, session, redirect, request, url_for, render_template
from requests_oauthlib import OAuth2Session
from os import environ


def token_updater(token):
    session['oauth2_token'] = token


class FlaskServer(Flask):
    def __init__(self, name, settings, sql, bot):
        Flask.__init__(self, name)
        self.settings = settings
        self.sql = sql
        self.bot = bot
        self.Api_Base_Url = environ.get('API_BASE_URL', 'https://discordapp.com/api')
        self.Authorization_Base_Url = self.Api_Base_Url + '/oauth2/authorize'
        self.Token_Url = self.Api_Base_Url + '/oauth2/token'

        self.config["SECRET_KEY"] = settings["discord_client_secret"]

        @self.route("/")
        def index():
            scope = request.args.get('scope', 'connections')
            discord = self.make_session(scope=scope.split(' '))
            authorization_url, state = discord.authorization_url(self.Authorization_Base_Url)
            session['oauth2_state'] = state
            return redirect(authorization_url)

        @self.route("/callback")
        def callback():
            if request.values.get('error'):
                return request.values['error']
            discord = self.make_session(state=session.get('oauth2_state'))
            token = discord.fetch_token(
                self.Token_Url,
                client_secret=self.settings['discord_client_secret'],
                authorization_response=request.url)
            session['oauth2_token'] = token

            user = discord.get(self.Api_Base_Url + '/users/@me').json()
            connections = discord.get(self.Api_Base_Url + '/users/@me/connections').json()
            found = False
            for entry in connections:
                if entry['type'] == 'steam':
                    found = True
                    self.sql.adduser(entry, user)
                    self.bot.bot.loop.create_task(self.bot.update_user(entry, user))
            do_template = self.settings['linked_template'].lower() != 'none' and self.settings['linked_template']
            return do_template and render_template(self.settings['linked_template'],
                                                   found=found) or found and 'Account Linked' or 'Steam account not linked to discord, link then try again.'

        self.run()

    def make_session(self, token=None, state=None, scope=None):
        oauth2_redirect_uri = self.settings['main_url'] + url_for('.callback')[1:]  # request.url +
        if 'http://' in oauth2_redirect_uri:
            environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
        return OAuth2Session(
            client_id=self.settings['discord_client_id'],
            token=token,
            state=state,
            scope=scope,
            redirect_uri=oauth2_redirect_uri,
            auto_refresh_kwargs={
                'client_id': self.settings['discord_client_id'],
                'client_secret': self.settings['discord_client_secret'],
            },
            auto_refresh_url=self.Token_Url,
            token_updater=token_updater)
