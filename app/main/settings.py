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

HOSTNAME = os.getenv('HOSTNAME', 'localhost')
ALLOWED_HOSTS = [ HOSTNAME, 'localhost', f'https://{HOSTNAME}']

CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

#CSRF_COOKIE_HTTPONLY = False

#SESSION_COOKIE_SECURE = True

#CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

print('ALLOWED_HOSTS:', ALLOWED_HOSTS)

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
ASGI_APPLICATION = 'mail.routing.application'

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


COOKIEBANNER = {
    "title": "Cookie settings",
    "header_text": "We are using cookies on this website. A few are essential, others are not.",
    "footer_text": "Please accept our cookies",
    "footer_links": [
        { "title": "Impprint", "href": "/imprint"},
        { "title": "Privacy", "href": "/privacy"},
    ],
    "groups": [
        {
            "id": "essential",
            "name": "Essential",
            "description": "Essential cookies allow this page to work.",
            "cookies": [
                {
                    "pattern": "cookiebanner",
                    "description": "Meta cookie for the cookies that are set.",
                },
                {
                    "pattern": "csrftoken",
                    "description": "This cookie prevents Cross-Site-Request-Forgery attacks.",
                },
                {
                    "pattern": "sessionid",
                    "description": "This cookie is necessary to allow logging in, for example.",
                },
            ],
        },
        {
            "id": "analytics",
            "name": "Analytics",
            "optional": True,
            "cookies": [
                {
                    "pattern": "_pk_.*",
                    "description": "Matomo cookie for website analysis.",
                },
            ],
        },
    ],
}

#REST_FRAMEWORK = {
#    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']
#}

# Email settings
EMAIL_HOST = os.getenv('EMAIL_HOST', None)

if EMAIL_HOST is not None:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', None) == 'True'
    EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', None) == 'True'
    EMAIL_PORT = os.getenv('EMAIL_PORT', None)
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@yourpipelines.com')

    print('Useing e-mail settings:')
    print(EMAIL_HOST)
    print(EMAIL_HOST_USER)
    print(EMAIL_PORT)
    print(DEFAULT_FROM_EMAIL)
