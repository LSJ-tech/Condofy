from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomTokenObtainPairSerializer, MembresiaSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Invalida el refresh token (requiere el blacklist app de simplejwt)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except (KeyError, TokenError):
            return Response({"detail": "refresh token inválido o ausente."}, status=400)
        return Response(status=205)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membresia = getattr(request.user, "membresia", None)
        if membresia is None:
            return Response({"detail": "Este usuario no tiene una membresía a ningún condominio."}, status=409)
        return Response(MembresiaSerializer(membresia).data)
