from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return Response(
            {"errors": response.data, "data": None, "meta": {}},
            status=response.status_code,
        )

    return Response(
        {"errors": [{"message": "An unexpected error occurred."}], "data": None, "meta": {}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
