import os
from pathlib import Path as P
from django.core.files.storage import FileSystemStorage

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = P(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
HOME_TITLE = os.getenv('HOME_TITLE', 'Django-3 Omics Pipelines')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.getenv('ENVIRONMENT') == 'develop')
print('DEBUG:', DEBUG)

ALLOWED_HOSTS = [ os.getenv('HOSTNAME'), 'localhost', 'web']

CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS
#CSRF_COOKIE_HTTPONLY = False
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'api',
    'user',
    'project',
    'maxquant',
    'dashboards',
    'rawtools',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'oauth2_provider',
    # 'sysmon',
    'cookielaw',
    'django_plotly_dash.apps.DjangoPlotlyDashConfig',
]

# ========================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'corsheaders.middleware.CorsMiddleware', # oauth2
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_currentuser.middleware.ThreadLocalUserMiddleware',
]

# django-plotly-dash
X_FRAME_OPTIONS = 'SAMEORIGIN'

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['/app/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'db',
        'PORT': 5432,
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = '/media'
STATIC_ROOT = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'main', "static"),
]


CELERY_BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'redis://redis:6379'


AUTH_USER_MODEL='user.User'
LOGIN_URL='/admin/login/'


OAUTH2_PROVIDER = {
    "OIDC_ENABLED": True,
    "OIDC_RSA_PRIVATE_KEY": os.environ.get("OIDC_RSA_PRIVATE_KEY"),
    "SCOPES": {
        "openid": "OpenID Connect scope",
    },
}


DATALAKE_ROOT = P('/datalake/')
COMPUTE_ROOT = P('/compute/')


class MediaFileSystemStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if max_length and len(name) > max_length:
            raise(Exception("name's length is greater than max_length"))
        return name
    
    def _save(self, name, content):
        if self.exists(name):
            return name
        return super(MediaFileSystemStorage, self)._save(name, content)

DATALAKE = MediaFileSystemStorage(location=str(DATALAKE_ROOT))
COMPUTE = MediaFileSystemStorage(location=str(COMPUTE_ROOT))
