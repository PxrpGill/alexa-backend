from .base import *

DEBUG = True

DATABASES['default']['HOST'] = config('DB_HOST', default='localhost')
