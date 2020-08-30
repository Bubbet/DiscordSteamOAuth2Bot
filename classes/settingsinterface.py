from json import dump, load
from json.decoder import JSONDecodeError
settings_path = "settings.json"


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
            with open(settings_path) as file:
                self.config = load(file)
        except (IOError, JSONDecodeError):
            self.config = {}
        self.get_from_user()
        self.save()

    def get_from_user(self):
        """List of values used in the script and their description, gathered by the loop."""
        values = {'discord_client_id': 'Discord Client ID',
                  'discord_client_secret': 'Discord Client Secret',
                  'discord_bot_token': 'Discord Bot Token',
                  'main_url': 'Url to be used before redirect',
                  'linked_template': 'Path to html file for link successful page (none for using default)',
                  'enable_link_command': 'True to enable the steam link command (which can have user error) or False'}
        for key, value in values.items():
            if not self[key]:
                self[key] = input(f'Enter your {value}:')

    def save(self):
        try:
            with open(settings_path, 'w') as file:
                dump(self.config, file, indent=2)
        except IOError as e:
            print(f'Error saving config. Exception: {e}')
