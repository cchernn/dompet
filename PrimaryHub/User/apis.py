from rest_framework import views, response, permissions, status
from .serializers import UserSerializer
from . import services
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterAPI(views.APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        data.instance = services.create_user(userdc=data)

        return response.Response(data=serializer.data)
    
class UserAPI(views.APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request):
        user = request.user

        serializer = UserSerializer(user)

        return response.Response(serializer.data)

class LogoutAPI(views.APIView):
    permission_classes = (permissions.IsAuthenticated, )
    
    def post(self, request):
        try:
            refresh_token = request.data['refresh_token']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return response.Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as ex:
            return response.Response(status=status.HTTP_400_BAD_REQUEST)
        
class VerifyEmailAPI(views.APIView):
    def get(self, request):
        username = request.data.get('username', None)
        email = request.data.get('email', None)

        user = services.get_user(username=username, email=email)
        if not user:
            return response.Response(status=status.HTTP_404_NOT_FOUND)
        
        return response.Response(status=status.HTTP_200_OK)