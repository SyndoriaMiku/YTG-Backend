from rest_framework import serializers
from django.utils import timezone
from . import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    nickname = serializers.CharField(max_length=30, required=False)

    class Meta:
        model = models.UserProfile
        fields = ['username', 'email', 'nickname', 'point', 'last_name_change']
        read_only_fields = ['username', 'email', 'point', 'last_name_change']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'phone']
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'phone': {'required': False, 'allow_blank': True},
        }

    def validate(self, data):
        email = data.get('email')
        phone = data.get('phone')

        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({_("Email is already in use.")})
        if phone and User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({_("Phone number is already in use.")})

        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class ChangeNicknameSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=30)

    def validate_nickname(self, value):
        if models.UserProfile.objects.filter(nickname=value).exists():
            raise serializers.ValidationError(_("This nickname is already taken."))
        return value

    def validate(self, attrs):
        user_profile = self.context['request'].user.userprofile
        if not user_profile.check_name_change_limit():
            raise serializers.ValidationError(_("You can only change your nickname once every 30 days."))
        return attrs

    def update(self, instance, validated_data):
        instance.nickname = validated_data['nickname']
        instance.last_name_change = timezone.now()
        instance.save()
        return instance
    
class PointTransactionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = models.PointTransaction
        fields = ['id', 'user', 'points', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user(self, obj):
        return obj.user.username
    def validate_points(self, value):
        if value == 0:
            raise serializers.ValidationError(_("Points cannot be zero."))
        return value
    def create(self, validated_data):
        return models.PointTransaction.objects.create(**validated_data)
    
class TournamentResultSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = models.TournamentResult
        fields = ['user', 'tournament_name', 'position', 'point_earned', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_user(self, obj):
        return obj.user.username
    def validate_point_earned(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Points earned cannot be negative."))
        return value
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
    user = serializers.SerializerMethodField()
    reward = serializers.PrimaryKeyRelatedField(queryset=models.Reward.objects.all())

    class Meta:
        model = models.RewardRedemption
        fields = ['user', 'reward', 'redeemed_at']
        read_only_fields = ['redeemed_at']

    def get_user(self, obj):
        return obj.user.username

    def validate(self, attrs):
        user = self.context['request'].user
        reward = attrs['reward']

        if user.userprofile.point < reward.cost:
            raise serializers.ValidationError(_("Insufficient points to redeem this reward."))

        if reward.stock <= 0:
            raise serializers.ValidationError(_("This reward is out of stock."))

        return attrs

    def create(self, validated_data):
        return models.RewardRedemption.objects.create(**validated_data)
