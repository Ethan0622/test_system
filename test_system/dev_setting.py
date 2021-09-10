# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# from sshtunnel import open_tunnel

# server = open_tunnel(('121.40.84.189', 22),
#                      ssh_username="root",
#                      ssh_password="Zc!@#123",
#                      remote_bind_address=('127.0.0.1', 3306),
#                      local_bind_address=('127.0.0.1', 5000))

# server.start()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'testsystem',
        'USER': 'root',
        # 'PASSWORD': 'Zc!@#123',
        'PASSWORD': '123456',
        'HOST': '127.0.0.1',
        # 'PORT': 5000,
    }
}