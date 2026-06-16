"""
Django settings module.
Import from local settings by default, or production/staging if DJANGO_ENV is set
"""
import os

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'production':
    from .production import *
elif env == 'staging':
    from .staging import *
else:
    from .local import *
