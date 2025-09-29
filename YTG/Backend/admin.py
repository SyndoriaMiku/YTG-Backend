from django.contrib import admin
from . import models
# Register your models here.

admin.site.register(models.UserProfile)
admin.site.register(models.Card)
admin.site.register(models.Booster)
admin.site.register(models.Order)
admin.site.register(models.OrderItem)
admin.site.register(models.PointTransaction)
admin.site.register(models.TournamentResult)
admin.site.register(models.Reward)
admin.site.register(models.RewardRedemption)
