from rest_framework import serializers
from .models import User
from .services import UserDataClass

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        read_only_fields = ["id"]
        extra_kwargs = {'password': {'write_only': True}}

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        
        return UserDataClass(**data)