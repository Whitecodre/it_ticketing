from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from apps.tickets.models import Ticket, Asset
from apps.common.models import Category

User = get_user_model()

class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            department='IT'
        )

    def test_user_creation(self):
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.get_full_name(), 'Test User')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_role_defaults_to_end_user(self):
        self.assertEqual(self.user.role, User.Role.END_USER)

    def test_user_get_full_name_with_role(self):
        self.assertEqual(
            self.user.get_full_name_with_role(),
            'Test User (User)'
        )

class LoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            department='IT',
            is_active=True,
            email_verified=True
        )
        self.login_url = reverse('accounts:login')

    def test_login_success(self):
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_failure(self):
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct email and password')

    def test_login_remember_me(self):
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'testpass123',
            'remember_me': 'on'
        })
        self.assertRedirects(response, reverse('dashboard'))
        # Session expiry should be 30 days
        self.assertEqual(self.client.session.get_expiry_age(), 30 * 24 * 60 * 60)

class TicketModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            department='IT'
        )
        self.category = Category.objects.create(name='Hardware', slug='hardware')

    def test_ticket_creation(self):
        ticket = Ticket.objects.create(
            number='TK#1234',
            title='Test Ticket',
            description='Test Description',
            requester=self.user,
            category=self.category,
            status=Ticket.Status.NEW
        )
        self.assertEqual(ticket.title, 'Test Ticket')
        self.assertEqual(ticket.requester, self.user)
        self.assertEqual(ticket.status, Ticket.Status.NEW)

    def test_ticket_priority_calculation(self):
        ticket = Ticket.objects.create(
            number='TK#1235',
            title='Test Ticket',
            description='Test Description',
            requester=self.user,
            category=self.category,
            impact=Ticket.Impact.ORGANIZATION,
            urgency=Ticket.Urgency.CRITICAL
        )
        self.assertEqual(ticket.priority, Ticket.Priority.P1)

    def test_ticket_string_representation(self):
        ticket = Ticket.objects.create(
            number='TK#1236',
            title='Test Ticket',
            description='Test Description',
            requester=self.user,
            category=self.category
        )
        self.assertEqual(str(ticket), 'TK#1236 - Test Ticket')

class AssetModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            department='IT'
        )

    def test_asset_creation(self):
        asset = Asset.objects.create(
            name='Test Laptop',
            asset_type='LAPTOP',
            serial_number='SN12345',
            status='ACTIVE',
            assigned_to=self.user
        )
        self.assertEqual(asset.name, 'Test Laptop')
        self.assertEqual(asset.assigned_to, self.user)
        self.assertIsNotNone(asset.tracking_id)
        self.assertTrue(asset.tracking_id.startswith('AST-'))

    def test_asset_string_representation(self):
        asset = Asset.objects.create(
            name='Test Laptop',
            asset_type='LAPTOP',
            status='ACTIVE'
        )
        self.assertIn('Test Laptop', str(asset))