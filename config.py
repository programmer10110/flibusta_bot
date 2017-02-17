# bot
TOKEN = ''
DEBUG = False
WEBHOOK = True


# botan
BOTAN_TOKEN = ''


# webhook
WEBHOOK_HOST = ''
WEBHOOK_PORT = 443
WEBHOOK_LISTEN = '0.0.0.0'

WEBHOOK_SSL_CERT = './cert/webhook_cert.pem'
WEBHOOK_SSL_PRIV = './cert/webhook_pkey.pem'

WEBHOOK_URL_BASE = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}"
WEBHOOK_URL_PATH = f"/{TOKEN}/"

# info
VERSION = "2.4.3"
DB_DATE = "17.02.2017"


# database
MYSQL_HOST = ''
MYSQL_DATABASE = ''
MYSQL_USER = ''
MYSQL_PASSWORD = ''


# users database
USERS_DATABASE = ''


# ftp_controller
LIFE_TIME = 3600  # seconds
FTP_DIR = './ftp'


#time
TIME_ZONE = 2


# tor
PROXIES = {'http': 'localhost:8118',
           'https': 'localhost:8118'}
