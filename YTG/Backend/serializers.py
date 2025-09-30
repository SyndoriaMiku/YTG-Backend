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
    ranking_point = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.UserProfile
        fields = ['username', 'email', 'nickname', 'point', 'ranking_point', 'last_name_change']
        read_only_fields = ['username', 'email', 'point', 'ranking_point', 'last_name_change']

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

        # Normalize empty strings to None so uniqueness works with NULLs
        if email == '':
            data['email'] = None
            email = None
        if phone == '':
            data['phone'] = None
            phone = None

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
    user = serializers.SlugRelatedField(slug_field='username', queryset=models.UserProfile.objects.all())

    class Meta:
        model = models.PointTransaction
        fields = ['id', 'user', 'points', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    def validate_points(self, value):
        if value == 0:
            raise serializers.ValidationError(_("Points cannot be zero."))
        return value
    def create(self, validated_data):
        return models.PointTransaction.objects.create(**validated_data)
    
class TournamentResultSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', queryset=models.UserProfile.objects.all())

    class Meta:
        model = models.TournamentResult
        fields = ['user', 'tournament_name', 'position', 'point_earned', 'ranking_point_earned', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_point_earned(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Points earned cannot be negative."))
        return value
    def validate_ranking_point_earned(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Ranking points earned cannot be negative."))
        return value

class TournamentBulkItemSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=30)
    tournament_name = serializers.CharField(max_length=255)
    position = serializers.CharField(max_length=255)
    point_earned = serializers.IntegerField(min_value=0, default=0)
    ranking_point_earned = serializers.IntegerField(min_value=0, default=0)

    def validate_nickname(self, value):
        if not models.UserProfile.objects.filter(nickname=value).exists():
            raise serializers.ValidationError(_("User with this nickname does not exist."))
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
        fields = ['user', 'reward', 'redeemed_at', 'status']
        read_only_fields = ['user', 'redeemed_at', 'status']

    def get_user(self, obj):
        return obj.user.username
    
    # Validation is deferred to admin confirmation step; creation is always allowed as pending
    def validate(self, attrs):
        return attrs
    
    def create(self, validated_data):
        validated_data['status'] = 'pending'
        return models.RewardRedemption.objects.create(**validated_data)

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = models.OrderItem
        fields = ['id', 'product_type', 'product_id', 'quantity', 'product_name', 'price']

    def get_product_name(self, obj):
        if obj.product_type == 'card':
            return models.Card.objects.get(id=obj.product_id).name
        elif obj.product_type == 'booster':
            return models.Booster.objects.get(id=obj.product_id).name
        return None
        return product.name if product else None
    
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    total_price = serializers.SerializerMethodField()

    class Meta:
        model = models.Order
        fields = ['id', 'user', 'status', 'created_at', 'updated_at', 'items', 'total_price']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.price * item.quantity for item in obj.items.all())