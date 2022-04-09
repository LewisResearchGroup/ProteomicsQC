from django.conf import settings


def variables(request):
    return {"ganalytics": settings.GANALYTICS}
