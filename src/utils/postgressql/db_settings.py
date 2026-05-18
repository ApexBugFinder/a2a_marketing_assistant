# Add these at the top of your settings.py
from os import getenv
from dotenv import load_dotenv
load_dotenv()
# Replace the DATABASES section of your settings.py with this
DATABASES = {
     'default': {
     'ENGINE': 'django.db.backends.postgresql',
     'NAME': getenv('DB_NAME'),
     'USER': getenv('DB_ROLE'),
     'PASSWORD': getenv('DB_PASSWORD'),
     'HOST': getenv('DB_HOSTNAME'),
     'PORT': getenv('DB_PORT', 5432),
     'OPTIONS': {
          'sslmode': 'require',
     },
     'DISABLE_SERVER_SIDE_CURSORS': True,
     'CONN_HEALTH_CHECKS': True,
     }
}