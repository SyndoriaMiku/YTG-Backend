from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext as _
from django.db import IntegrityError
from django.db.models import Sum, Q, F
from django.db import transaction
from django.utils import timezone

from . import serializers
from . import models
from . import permissions
# Create your views here.


class LoginAPIView(APIView):
    """
    API view for user login.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            is_admin = user.is_staff or user.is_superuser

            return Response({
                'message': _('Login successful'),
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'is_admin': is_admin,
                'username': user.username,
            })
        else:
            return Response({'message': _('Invalid credentials')}, status=status.HTTP_401_UNAUTHORIZED)
        
class RegisterAPIView(APIView):
    """
    API view for user registration.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': _('User registered successfully'),
                'username': user.username,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutAPIView(APIView):
    """
    API view for user logout.
    """
    # AllowAny so clients can log out using refresh token without a valid access token
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response({'message': _('Refresh token is required')}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': _('Logout successful')}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'message': _('Invalid token')}, status=status.HTTP_400_BAD_REQUEST)
        
class UpdateUserAPIView(APIView):
    """
    API view for updating user profile.
    """
    permission_classes = [IsAuthenticated]

    def patch(self , request):
        user = request.user
        data = request.data

        updated_fields = []

        #update data
        if 'email' in data:
            # Normalize blank string to None to satisfy DB unique constraint
            user.email = data['email'] or None
            updated_fields.append('email')

        if 'phone' in data:
            user.phone = data['phone']
            updated_fields.append('phone') 
        
        if 'nickname' in data:
            new_nickname = data['nickname']
            if user.nickname != new_nickname:
                if user.check_name_change_limit():
                    user.nickname = new_nickname
                    user.last_name_change = timezone.now()
                    updated_fields.extend(['nickname', 'last_name_change'])
                else:
                    return Response({'message': _('You can only change your nickname once every 30 days.')}, status=status.HTTP_400_BAD_REQUEST)
                
        #Update if changes were made
        try:
            if updated_fields:
                user.save(update_fields=updated_fields)
                return Response({'message': _('User profile updated successfully')}, status=status.HTTP_200_OK)
            else:
                return Response({'message': _('No changes made to the profile')}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({'message': _('Error updating profile')}, status=status.HTTP_400_BAD_REQUEST)
        
class AdminAdjustPointAPIView(APIView):
    """
    API view for admin to adjust points to a user.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = serializers.PointTransactionSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data.get('user')
            points = serializer.validated_data.get('points')
            description = serializer.validated_data.get('description', '')

            # Create the point transaction
            point_transaction = models.PointTransaction.objects.create(
                user=user,
                points=points,
                description=description
            )
            # Update user's point balance
            user.point += points
            user.save()

            return Response({
                'message': _('Points added successfully'),
                'user': user.username,
                'points': point_transaction.points,
                'description': point_transaction.description
            }, status=status.HTTP_201_CREATED)
        return Response({'message': _('Invalid data')}, status=status.HTTP_400_BAD_REQUEST)
    
class AdminTournamentResultAPIView(APIView):
    """
    API view for admin to add tournament results.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = serializers.TournamentResultSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data.get('user')
            tournament_name = serializer.validated_data.get('tournament_name')
            position = serializer.validated_data.get('position')
            point_earned = serializer.validated_data.get('point_earned', 0)
            ranking_point_earned = serializer.validated_data.get('ranking_point_earned', 0)

            # Create the tournament result
            tournament_result = models.TournamentResult.objects.create(
                user=user,
                tournament_name=tournament_name,
                position=position,
                point_earned=point_earned,
                ranking_point_earned=ranking_point_earned
            )

            # Update user's ranking_point (for ranking only) and spendable point separately
            if ranking_point_earned:
                user.ranking_point += ranking_point_earned
            if point_earned:
                user.point += point_earned
            user.save(update_fields=['ranking_point', 'point'])

            return Response({
                'message': _('Tournament result added successfully'),
                'user': user.username,
                'tournament_name': tournament_result.tournament_name,
                'position': tournament_result.position,
                'point_earned': tournament_result.point_earned
            }, status=status.HTTP_201_CREATED)
        return Response({'message': _('Invalid data')}, status=status.HTTP_400_BAD_REQUEST)

class AdminTournamentBulkUpdateAPIView(APIView):
    """
    Admin bulk create/update tournament results from JSON array of items.
    Each item: nickname, tournament_name, position, point_earned, ranking_point_earned
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list) or not items:
            return Response({'message': _('Invalid payload. Expecting a non-empty list.')}, status=status.HTTP_400_BAD_REQUEST)

        item_serializer = serializers.TournamentBulkItemSerializer(data=items, many=True)
        if not item_serializer.is_valid():
            return Response(item_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        results = []
        errors = []

        for idx, data in enumerate(item_serializer.validated_data):
            try:
                with transaction.atomic():
                    user = models.UserProfile.objects.select_for_update().get(nickname=data['nickname'])
                    tr = models.TournamentResult.objects.create(
                        user=user,
                        tournament_name=data['tournament_name'],
                        position=data['position'],
                        point_earned=data.get('point_earned', 0),
                        ranking_point_earned=data.get('ranking_point_earned', 0)
                    )
                    # Update user counters
                    if data.get('ranking_point_earned', 0):
                        user.ranking_point += data['ranking_point_earned']
                    if data.get('point_earned', 0):
                        user.point += data['point_earned']
                    user.save(update_fields=['ranking_point', 'point'])
                    results.append({
                        'nickname': user.nickname,
                        'tournament_name': tr.tournament_name,
                        'position': tr.position,
                        'point_earned': tr.point_earned,
                        'ranking_point_earned': tr.ranking_point_earned,
                    })
            except Exception as exc:
                errors.append({'index': idx, 'nickname': data['nickname'], 'error': str(exc)})

        status_code = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED
        return Response({'results': results, 'errors': errors}, status=status_code)
    
class UserPointAPIView(APIView):
    """
    API view for users to view their point balance.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username,
            'points': request.user.point
        }, status=status.HTTP_200_OK)

class PointTransactionHistoryAPIView(APIView):
    """
    API view for users to view their point transactions.
    """
    permission_classes = [IsAuthenticated]

    def get (self, request):
        if request.user.is_staff or request.user.is_superuser and "user" in request.query_params:
            user = request.query_params.get("user")
            transactions = models.PointTransaction.objects.filter(user__username=user)
        else:
            transactions = models.PointTransaction.objects.filter(user=request.user)

        serializer = serializers.PointTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RedeemRewardAPIView(APIView):
    """
    API view for users to redeem rewards.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = serializers.RewardRedemptionSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Always allow creation as pending; enforcement happens in admin confirm
        user = request.user
        reward = serializer.validated_data.get('reward')
        redemption = models.RewardRedemption.objects.create(
            user=user,
            reward=reward,
            status='pending'
        )
        return Response({
            'message': _('Your redemption request has been created'),
            'redemption_id': redemption.id,
            'status': redemption.status,
        }, status=status.HTTP_201_CREATED)
    
class AdminRedemptionAPIView(APIView):
    """
    API view for admin to confirm or reject reward redemptions.
    """
    permission_classes = [permissions.IsStaffUser]
    def post(self, request, redemption_id):
        redemption = get_object_or_404(models.RewardRedemption, id=redemption_id)

        if redemption.status != 'pending':
            return Response({'message': _('This redemption has already been processed')}, status=status.HTTP_400_BAD_REQUEST)
        
        user = redemption.user
        reward = redemption.reward

        if user.point < reward.cost:
            return Response({'message': _('User does not have enough points to redeem this reward')}, status=status.HTTP_400_BAD_REQUEST)
        if reward.stock <= 0:
            return Response({'message': _('This reward is out of stock')}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update user's points and reward stock
        user.point -= reward.cost
        user.save()
        reward.stock -= 1
        reward.save()

        # Update redemption status
        redemption.status = 'completed'
        redemption.save()

        # Record point transaction as spent
        models.PointTransaction.objects.create(
            user=user,
            points=-reward.cost,
            description=f"Redeemed: {reward.name}"
        )

        return Response({
            'message': _('Redemption confirmed successfully'),
        }, status=status.HTTP_200_OK)
    
class AdminCancelRedemptionAPIView(APIView):
    """
    API view for admin to cancel reward redemptions.
    """
    permission_classes = [permissions.IsStaffUser]

    def post(self, request, redemption_id):
        redemption = get_object_or_404(models.RewardRedemption, id=redemption_id)

        if redemption.status != 'pending':
            return Response({'message': _('This redemption cannot be cancelled')}, status=status.HTTP_400_BAD_REQUEST)

        # Update redemption status to cancelled
        redemption.status = 'cancelled'
        redemption.save()

        return Response({
            'message': _('Redemption cancelled successfully'),
        }, status=status.HTTP_200_OK)
        
    
# Order API Views

class CreateOrderAPIView(APIView):
    """
    API view for creating an order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = models.Order.objects.create(user=request.user, total_price=0)

        items_data = request.data.get('items', [])
        total_price = 0

        for item in items_data:
            product_type = item.get('product_type')
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)

            if product_type == 'card':
                product = get_object_or_404(models.Card, id=product_id)
            elif product_type == 'booster':
                product = get_object_or_404(models.Booster, id=product_id)
            else:
                return Response({'message': _('Invalid product type')}, status=status.HTTP_400_BAD_REQUEST)
            
            if product.stock < quantity:
                return Response({'message': _('Insufficient stock for product')}, status=status.HTTP_400_BAD_REQUEST)
            
            price = product.price * quantity
            total_price += price

            #Reduce stock
            product.stock -= quantity
            product.save()

            # Create order item
            order_item = models.OrderItem.objects.create(
                order=order,
                product_type=product_type,
                product_id=product_id,
                quantity=quantity,
                price=price
            )

        # Update order total price
        order.total_price = total_price
        order.save()

        return Response({
            'message': _('Order created successfully'),
            'order_id': order.id,
            'total_price': order.total_price,
            'items': serializers.OrderItemSerializer(order.items.all(), many=True).data
        }, status=status.HTTP_201_CREATED)
    
class UserOrderView(APIView):
    """
    API view for users to view all their orders.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = models.Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = serializers.OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class OrderDetailView(APIView):
    """
    API view for users to view details of a specific order.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(models.Order, id=order_id, user=request.user)
        serializer = serializers.OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class CancelOrderAPIView(APIView):
    """
    API view for users to cancel an order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        if not request.user.is_staff and not request.user.is_superuser:
            order = get_object_or_404(models.Order, id=order_id, user=request.user)
        else:
            order = get_object_or_404(models.Order, id=order_id)

        if order.status == 'cancelled':
            return Response({'message': _('Order is already cancelled')}, status=status.HTTP_400_BAD_REQUEST)

        if order.status != 'pending':
            return Response({'message': _('Only pending orders can be cancelled')}, status=status.HTTP_400_BAD_REQUEST)
        
        #Update order status
        order.status = 'cancelled'
        order.save()

        return Response({
            'message': _('Order cancelled successfully'),
            'order_id': order.id
        }, status=status.HTTP_200_OK)
        
# Ranking API Views        
class MonthlyRankingAPIView(APIView):
    """
    API view for getting monthly ranking.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # Validate date parameters
        try:
            start = timezone.datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
            if month == 12:
                end = timezone.datetime(year + 1, 1, 1, tzinfo=timezone.get_current_timezone())
            else:
                end = timezone.datetime(year, month + 1, 1, tzinfo=timezone.get_current_timezone())
        except ValueError:
            return Response(
                {'error': _('Invalid year or month')}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use TournamentResult to compute monthly ranking points earned
        qs = models.TournamentResult.objects.filter(created_at__gte=start, created_at__lt=end)
        
        aggregated = qs.values('user__username').annotate(
            ranking_earned=Sum('ranking_point_earned')
        ).order_by('-ranking_earned')
        
        # Manual pagination
        total_items = aggregated.count()
        total_pages = (total_items + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        results = []
        for row in aggregated[start_idx:end_idx]:
            results.append({
                'nickname': row['user__nickname'],
                'ranking_earned': row['ranking_earned'] or 0,
            })

        return Response({
            'year': year,
            'month': month,
            'current_page': page,
            'total_pages': total_pages,
            'page_size': page_size,
            'total_items': total_items,
            'results': results
        }, status=status.HTTP_200_OK)
