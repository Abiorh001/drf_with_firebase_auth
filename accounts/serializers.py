from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'firebase_uid', 'email', 'password', 'first_name', 'last_name']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance
    
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class UserUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ['id', 'email', 'firebase_uid', 'first_name', 'last_name']
        read_only_fields = ['id', 'email', 'firebase_uid']


class UserEmailUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    firebase_uid = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'firebase_uid', 'first_name', 'last_name']
        read_only_fields = ['id', 'first_name', 'last_name']