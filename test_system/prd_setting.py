# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'testsystem',
        'USER': 'root',
        'PASSWORD': 'Zc!@#123',
        'HOST': '127.0.0.1',
    }
}