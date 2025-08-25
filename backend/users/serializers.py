from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo User.
    Converte objetos User para JSON e vice-versa, expondo apenas campos seguros.
    """
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number'
        ]
        extra_kwargs = { 'password': { 'write_only': True } }
        read_only_fields = ['id']