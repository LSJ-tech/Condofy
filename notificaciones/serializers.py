from rest_framework import serializers

from .models import DispositivoPush


class DispositivoPushSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositivoPush
        fields = ["id", "token", "plataforma"]
