from rest_framework.views import APIView
from rest_framework.exceptions import NotFound


class APINotFoundView(APIView):
    """
    Fallback view to catch all unhandled /api/* routing patterns
    and return a native DRF 404 response.
    """

    def initial(self, request, *args, **kwargs):
        # Triggering permission/auth lifecycle hooks if needed,
        # then immediately raising the DRF NotFound error.
        raise NotFound(detail="The resource you are looking for is not found.")
