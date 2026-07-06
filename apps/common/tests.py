from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.common.models import Category, Tag, Notification, PushSubscription

User = get_user_model()


class CategoryModelTests(TestCase):
    """Test Category model."""

    def test_category_creation(self):
        category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            description='Test description'
        )
        self.assertEqual(category.name, 'Test Category')
        self.assertEqual(category.slug, 'test-category')
        self.assertEqual(str(category), 'Test Category')

    def test_category_parent_relationship(self):
        parent = Category.objects.create(name='Parent', slug='parent')
        child = Category.objects.create(
            name='Child',
            slug='child',
            parent=parent
        )
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())


class TagModelTests(TestCase):
    """Test Tag model."""

    def test_tag_creation(self):
        tag = Tag.objects.create(name='test-tag')
        self.assertEqual(tag.name, 'test-tag')
        self.assertEqual(str(tag), 'test-tag')


class PushSubscriptionModelTests(TestCase):
    """Test PushSubscription model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT'
        )

    def test_push_subscription_creation(self):
        sub = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://example.com/endpoint',
            auth_key='auth123',
            p256dh_key='p256dh123'
        )
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.endpoint, 'https://example.com/endpoint')
        self.assertEqual(str(sub), f'PushSubscription for {self.user.email}')


class NotificationModelTests(TestCase):
    """Test Notification model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT'
        )

    def test_notification_creation(self):
        notification = Notification.objects.create(
            recipient=self.user,
            message='Test notification',
            url='/dashboard/',
            type=Notification.Type.GENERAL
        )
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.message, 'Test notification')
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.type, Notification.Type.GENERAL)
        self.assertEqual(str(notification), f'Notification for {self.user.email}: Test notification')

    def test_notification_mark_read(self):
        notification = Notification.objects.create(
            recipient=self.user,
            message='Test notification',
            url='/dashboard/'
        )
        self.assertFalse(notification.is_read)
        notification.is_read = True
        notification.save()
        self.assertTrue(notification.is_read)

    def test_notification_unread_count(self):
        """Test unread notification count."""
        Notification.objects.create(recipient=self.user, message='Notif 1', url='/')
        Notification.objects.create(recipient=self.user, message='Notif 2', url='/')
        Notification.objects.create(recipient=self.user, message='Notif 3', url='/')

        notif = Notification.objects.filter(recipient=self.user).first()
        notif.is_read = True
        notif.save()

        count = Notification.objects.filter(recipient=self.user, is_read=False).count()
        self.assertEqual(count, 2)