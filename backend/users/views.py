from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserRegisterSerializer
from .serializers import CustomTokenObtainPairSerializer
from .permissions import IsAdmin

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        """
        Permissions différentes selon l'action
        """
        if self.action == 'create':
            permission_classes = [AllowAny]  # L'inscription est publique
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]   # Seul l'admin peut modifier/supprimer
        else:
            permission_classes = [IsAuthenticated]  # Les autres actions nécessitent auth
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Récupérer le profil de l'utilisateur connecté"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Changer le mot de passe"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({'error': 'Ancien mot de passe incorrect'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Mot de passe changé avec succès'})

class RegisterView(generics.CreateAPIView):
    """Inscription publique"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegisterSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    """Connexion avec email + mot de passe"""
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

class LogoutView(generics.GenericAPIView):
    """Déconnexion (blacklist du refresh token)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        



