from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

import random
import string

def generate_id(length=7):
    """Generate a random alphanumeric ID of specified length."""
    while True:
        id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not PointTransaction.objects.filter(id=id).exists():
            return id


Rarity_CHOICES = [
    ('common', 'Common'),
    ('rare', 'Rare'),
    ('parallel rare', 'Parallel Rare'),
    ('gold rare', 'Gold Rare'),
    ('super rare', 'Super Rare'),
    ('super parallel rare', 'Super Parallel Rare'),
    ('platinum rare', 'Platinum Rare'),
    ('ultra rare', 'Ultra Rare'),
    ('ultra parallel rare', 'Ultra Parallel Rare'),
    ('gold secret rare', 'Gold Secret Rare'),
    ('premium gold rare', 'Premium Gold Rare'),
    ('secret rare', 'Secret Rare'),
    ('prismatic secret rare', 'Prismatic Secret Rare'),
    ('secret parallel rare', 'Secret Parallel Rare'),
    ('extra secret rare', 'Extra Secret Rare'),
    ('platinum secret rare', 'Platinum Secret Rare'),
    ('collector rare', 'Collector Rare'),
    ('quarter century secret rare', 'Quarter Century Secret Rare'),
    ('ultimate rare', 'Ultimate Rare'),
    ('ghost rare', 'Ghost Rare'),
    ('starlight rare', 'Starlight Rare'),
    ('holographic rare', 'Holographic Rare'),
]

Status_CHOICES = [
    ('pending', 'Pending'), #User created order, waiting for confirmation
    ('confirmed', 'Confirmed'), #Admin confirmed the order
    ('completed', 'Completed'), #Order completed, user received the products
    ('cancelled', 'Cancelled'), #Order cancelled by user or admin
]
    

# === Product ====

# Create your models here.

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products_image/', null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name
    
class Card(Product):
    card_code = models.CharField(max_length=10)
    version = models.CharField(max_length=255, default='v1')
    rarity = models.CharField(max_length=50, choices=Rarity_CHOICES)

class Booster(Product):
    booster_code = models.CharField(max_length=10)
    version = models.CharField(max_length=255, default='v1')

# === Order === 

class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=Status_CHOICES, default='pending')

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('can_confirm_order', 'Can confirm order'),
        ]

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_type = models.CharField(max_length=50)  # 'card' or 'booster'
    product_id = models.IntegerField()  # ID of the Card or Booster
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_type} (ID: {self.product_id}) in Order {self.order.id}"
    
# === Transactions ===

class PointTransaction(models.Model):
    id = models.CharField(primary_key=True, max_length=7, editable=False, default=generate_id)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    points = models.IntegerField() #positive or negative
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} {'earned' if self.points > 0 else 'spent'} {abs(self.points)} points on {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class TournamentResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tournament_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    point_earned = models.IntegerField(default=0)
    ranking_point_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.tournament_name} - {self.position} - {self.point_earned} points"
    
class Reward(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    cost = models.IntegerField(default=0)
    stock = models.IntegerField(default=0)
    image = models.ImageField(upload_to='rewards_image/', null=True, blank=True)

    def __str__(self):
        return self.name
    
class RewardRedemption(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=Status_CHOICES, default='pending')

    def __str__(self):
        return f"{self.user.username} redeemed {self.reward.name} on {self.redeemed_at.strftime('%Y-%m-%d %H:%M:%S')}"
    class Meta:
        unique_together = ('user', 'reward', 'status')
        ordering = ['-redeemed_at']

class UserProfile(AbstractUser):
    nickname = models.CharField(max_length=30)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    point = models.IntegerField(default=0)
    ranking_point = models.IntegerField(default=0)
    last_name_change = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Coerce blank email strings to NULL to satisfy unique constraint in MySQL
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)

    def check_name_change_limit(self):
        """Check if the user can change their name based on the last change time."""
        if self.last_name_change:
            return timezone.now() - self.last_name_change >= timedelta(days=30)
        return True

    def __str__(self):
        return self.username
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['username']    
