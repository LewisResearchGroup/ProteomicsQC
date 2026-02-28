from pathlib import Path as P
from django.core.exceptions import ValidationError


def validate_file_is_rawfile(value):
    ext = P(value.name).suffix.lower()
    valid_extensions = [".raw"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("Unsupported file extension.")
