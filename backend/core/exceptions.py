from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework.exceptions import APIException


class Error(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A custom business error occurred."
    default_code = "custom_error"

    def __init__(self, detail=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail


def global_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # If response is None, it means a raw Python crash happened (e.g., KeyError, ValueError)
    if response is None and not settings.DEBUG:
        return Response(
            {"detail": "Internal Server Error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
