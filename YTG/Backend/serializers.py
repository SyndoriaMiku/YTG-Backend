from rest_framework import serializers
from django.utils import timezone
import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    nickname = serializers.CharField(max_length=30, required=False)

    class Meta:
        model = models.UserProfile
        fields = ['username', 'email', 'nickname', 'point', 'last_name_change']
        read_only_fields = ['point', 'last_name_change']


class ChangeNicknameSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=30)

    def validate_nickname(self, value):
        if models.UserProfile.objects.filter(nickname=value).exists():
            raise serializers.ValidationError("This nickname is already taken.")
        return value

    def validate(self, attrs):
        user_profile = self.context['request'].user.userprofile
        if not user_profile.check_name_change_limit():
            raise serializers.ValidationError("You can only change your nickname once every 30 days.")
        return attrs

    def update(self, instance, validated_data):
        instance.nickname = validated_data['nickname']
        instance.last_name_change = timezone.now()
        instance.save()
        return instance
    
class PointTransactionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    points = serializers.IntegerField()

    class Meta:
        model = models.PointTransaction
        fields = ['id', 'user', 'points', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        return models.PointTransaction.objects.create(**validated_data)
    
class TournamentResultSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = models.TournamentResult
        fields = ['user', 'tournament_name', 'position', 'point_earned', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        return models.TournamentResult.objects.create(**validated_data)
    
class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Reward
        fields = ['id', 'name', 'description', 'cost', 'stock', 'image']
        read_only_fields = ['id']

    def create(self, validated_data):
        return models.Reward.objects.create(**validated_data)
    
class RewardRedemptionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    reward = serializers.CharField(source='reward.name', read_only=True)

    class Meta:
        model = models.RewardRedemption
        fields = ['user', 'reward', 'redeemed_at']
        read_only_fields = ['redeemed_at']

    def create(self, validated_data):
        return models.RewardRedemption.objects.create(**validated_data)
    def validate(self, attrs):
        user = self.context['request'].user
        reward = attrs['reward']
        
        if user.userprofile.point < reward.cost:
            raise serializers.ValidationError("Insufficient points to redeem this reward.")
        
        if reward.stock <= 0:
            raise serializers.ValidationError("This reward is out of stock.")
        
        return attrs
