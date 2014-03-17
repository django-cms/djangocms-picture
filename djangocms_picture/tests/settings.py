DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = ('django.contrib.auth',
                  'django.contrib.admin',
                  'django.contrib.contenttypes',
                  'django.contrib.sessions',
                  'django.contrib.sites',

                  'cms',
                  'mptt',

                  'djangocms_picture')

SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

TEMPLATE_CONTEXT_PROCESSORS = ('django.core.context_processors.request',)
