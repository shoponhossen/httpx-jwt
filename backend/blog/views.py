from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from core.exceptions import Error
from rest_framework.permissions import IsAuthenticated


class NonAuthView(APIView):
    throttle_scope = "test"

    def get(self, request: Request, type: str):

        if type == "keyerror":
            a = {"a": "A", "b": "B"}
            print(a["c"])

        elif type == "valueerror":
            raise ValueError("Value Error")

        elif type == "error":
            raise Error("Custom Error X@")

        data = {"message": "Hello from non-auth view!"}

        return Response(data, status=status.HTTP_200_OK)


class AuthView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, r: Request):
        data = {"message": f"Hello {r.user}"}
        return Response(data, status=status.HTTP_200_OK)
