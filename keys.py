

SYSTEM_IDS =['accio', 'aguamenti', 'expecto patronum', 'diffindo', 'episkey', 'expelliarmus', 'impedimenta',
 'protego', 'revelio', 'tergeo',  'lumos', 'veritaserum', 'muffliato', 'alohomora', 'test']
GOOGLE_SPREADSHEET_ID = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# set app icon
from kivy.config import Config
from os.path import dirname, join

CURDIR = dirname(__file__)
icon_path = join(CURDIR, 'icons', 'simpleicon.png')
Config.set('kivy', 'window_icon', icon_path)
CONFIG_FILE = join(CURDIR, 'kivycam.ini')