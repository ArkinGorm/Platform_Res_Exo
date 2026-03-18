from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']
        read_only_fields = ['id']

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email', 'role']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # 1. On définit email et password
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
    
    # 2. On écrase la définition du parent pour rendre username optionnel
    username = serializers.CharField(required=False, allow_blank=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 3. Sécurité supplémentaire : on retire 'username' des champs requis
        self.fields['username'].required = False

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        # Recherche de l'utilisateur par email
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "Utilisateur introuvable"})

        # Authentification (Django utilise le username interne)
        user = authenticate(username=user_obj.username, password=password)

        if not user:
            raise serializers.ValidationError({"password": "Mot de passe incorrect"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Compte désactivé"})

        # Génération manuelle du token
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "role": getattr(user, 'role', None), # Sécurité si role n'existe pas
            }
        }