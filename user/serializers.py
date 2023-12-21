from rest_framework import serializers
from .models import User
from .services import UserDataClass

class UserSerializer(serializers.ModelSerializer):
    group_names = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "is_superuser", "is_active", "user_permissions", "groups", "group_names"]
        read_only_fields = ["id", "is_superuser", "user_permissions", "groups", "group_names"]
        extra_kwargs = {'password': {'write_only': True}}

    def get_group_names(self, obj):
        if 'groups' in obj.__dict__:
            return list(obj.groups.values_list('name', flat=True))
        else:
            return []

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        
        return UserDataClass(**data)