from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LogoutSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Create a new account. Returns the user (log in separately to get tokens)."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class LogoutView(APIView):
    """
    JWTs cannot be "deleted", so logout blacklists the refresh token.
    After this, the refresh token can no longer be used to get new access tokens.
    """

    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            raise ValidationError({"refresh": ["Token is invalid or expired."]})
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    """The currently logged-in user."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
