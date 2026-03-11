from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Permission pour les administrateurs uniquement
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsParticipant(permissions.BasePermission):
    """
    Permission pour les participants uniquement
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'participant'

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission: l'utilisateur peut modifier ses propres objets, sinon lecture seule
    """
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour tous
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Écriture autorisée seulement pour le propriétaire
        return obj.user == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission: les admins peuvent tout faire, les autres en lecture seule
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role == 'admin'