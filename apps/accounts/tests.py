from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

User = get_user_model()


class UserModelTests(TestCase):
    """Test User model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT',
            role=User.Role.END_USER
        )

    def test_user_creation(self):
        """Test basic user creation."""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.get_full_name(), 'Test User')
        self.assertTrue(self.user.check_password('TestPass123!'))
        self.assertEqual(self.user.role, User.Role.END_USER)

    def test_user_creation_with_email_normalization(self):
        """Test email is normalized (lowercased)."""
        user = User.objects.create_user(
            email='TEST@EXAMPLE.COM',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT'
        )
        self.assertEqual(user.email, 'test@example.com')

    def test_user_get_full_name_with_role(self):
        """Test get_full_name_with_role method."""
        result = self.user.get_full_name_with_role()
        self.assertEqual(result, 'Test User (User)')

    def test_user_superuser_creation(self):
        """Test superuser creation."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            department='IT'
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertEqual(admin.role, User.Role.SUPERADMIN)

    def test_user_role_auto_sets_staff(self):
        """Test that certain roles auto-set is_staff."""
        roles_with_staff = [
            User.Role.SUPERADMIN,
            User.Role.ADMIN,
            User.Role.TEAM_LEAD,
            User.Role.AGENT
        ]
        for role in roles_with_staff:
            user = User.objects.create_user(
                email=f'{role}@example.com',
                password='TestPass123!',
                first_name='Test',
                last_name='User',
                department='IT',
                role=role
            )
            self.assertTrue(user.is_staff)

    def test_user_end_user_not_staff(self):
        """Test that END_USER role does not set is_staff."""
        user = User.objects.create_user(
            email='enduser@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT',
            role=User.Role.END_USER
        )
        self.assertFalse(user.is_staff)


class RegistrationTests(TestCase):
    """Test user registration flow."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')

    def test_registration_page_loads(self):
        """Test registration page loads successfully."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register_step1.html')

    def test_registration_step1_valid(self):
        """Test step 1 of registration with valid data."""
        response = self.client.post(self.register_url, {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'department': 'IT'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=2', response.url)

    def test_registration_step1_duplicate_email(self):
        """Test step 1 with duplicate email."""
        User.objects.create_user(
            email='existing@example.com',
            password='TestPass123!',
            first_name='Existing',
            last_name='User',
            department='IT'
        )
        response = self.client.post(self.register_url, {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'existing@example.com',
            'department': 'IT'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A user with this email already exists')

    def test_registration_step2_valid(self):
        """Test step 2 with valid password."""
        session = self.client.session
        session['registration_data'] = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'department': 'IT'
        }
        session.save()

        response = self.client.post(f'{self.register_url}?step=2', {
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register_done.html')

        user = User.objects.filter(email='newuser@example.com').first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)

    def test_registration_step2_password_mismatch(self):
        """Test step 2 with mismatched passwords."""
        session = self.client.session
        session['registration_data'] = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'department': 'IT'
        }
        session.save()

        response = self.client.post(f'{self.register_url}?step=2', {
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')

    def test_registration_step2_password_too_short(self):
        """Test step 2 with password shorter than 10 characters."""
        session = self.client.session
        session['registration_data'] = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'department': 'IT'
        }
        session.save()

        response = self.client.post(f'{self.register_url}?step=2', {
            'password1': 'Short1!',
            'password2': 'Short1!'
        })
        self.assertEqual(response.status_code, 200)
        # Django's password validation should catch this
        self.assertContains(response, 'password')


class LoginTests(TestCase):
    """Test login functionality."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT',
            is_active=True,
            email_verified=True
        )

    def test_login_page_loads(self):
        """Test login page loads successfully."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_failure_wrong_password(self):
        """Test login with wrong password."""
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'WrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct email and password')

    def test_login_failure_nonexistent_user(self):
        """Test login with nonexistent user."""
        response = self.client.post(self.login_url, {
            'username': 'nonexistent@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct email and password')

    def test_login_inactive_user(self):
        """Test login with inactive user."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'account has been deactivated')

    def test_login_unverified_email(self):
        """Test login with unverified email."""
        # Unverified users should be redirected to verification page
        self.user.email_verified = False
        self.user.save()

        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'TestPass123!'
        })
        # Should redirect to verification page or show message
        self.assertNotEqual(response.status_code, 200)
        # It might redirect to login page with error or to verification page

    def test_login_remember_me(self):
        """Test remember me functionality."""
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'TestPass123!',
            'remember_me': 'on'
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.client.session.get_expiry_age(), 30 * 24 * 60 * 60)

    def test_login_without_remember_me(self):
        """Test login without remember me."""
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('dashboard'))
        # Session should expire on browser close (0) or default
        self.assertIn(self.client.session.get_expiry_age(), [0, 86400])


class PasswordResetTests(TestCase):
    """Test password reset flow."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT',
            is_active=True,
            email_verified=True
        )
        self.reset_url = reverse('accounts:password_reset')

    def test_password_reset_page_loads(self):
        """Test password reset page loads."""
        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset.html')

    def test_password_reset_request_valid_email(self):
        """Test password reset request with valid email."""
        response = self.client.post(self.reset_url, {'email': 'test@example.com'})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('password reset', mail.outbox[0].subject.lower())

    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email."""
        response = self.client.post(self.reset_url, {'email': 'nonexistent@example.com'})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_valid(self):
        """Test password reset confirmation with valid token."""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.get(
            reverse('accounts:password_reset_confirm', args=[uid, token])
        )
        # Should show the reset form
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirmation with invalid token."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse('accounts:password_reset_confirm', args=[uid, 'invalid-token'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid or has expired')

    def test_password_reset_complete(self):
        """Test password reset complete flow."""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        # POST to the confirm URL with new password
        response = self.client.post(
            reverse('accounts:password_reset_confirm', args=[uid, token]),
            {
                'new_password1': 'NewStrongPass123!',
                'new_password2': 'NewStrongPass123!'
            }
        )
        # Should redirect to complete page
        self.assertRedirects(response, reverse('accounts:password_reset_complete'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass123!'))


class ProfileTests(TestCase):
    """Test user profile functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT',
            is_active=True,
            email_verified=True
        )
        self.client.login(email='test@example.com', password='TestPass123!')
        self.profile_url = reverse('accounts:profile')

    def test_profile_page_loads(self):
        """Test profile page loads for authenticated user."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboards/profile.html')

    def test_profile_update(self):
        """Test updating profile information."""
        response = self.client.post(self.profile_url, {
            'save_profile': '1',
            'first_name': 'Updated',
            'last_name': 'Name',
            'department': 'IT'
        })
        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')

    def test_password_change_valid(self):
        """Test changing password with valid data."""
        response = self.client.post(self.profile_url, {
            'change_password': '1',
            'old_password': 'TestPass123!',
            'new_password1': 'NewStrongPass123!',
            'new_password2': 'NewStrongPass123!'
        })
        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass123!'))

    def test_password_change_invalid_old(self):
        """Test changing password with invalid old password."""
        response = self.client.post(self.profile_url, {
            'change_password': '1',
            'old_password': 'WrongPass123!',
            'new_password1': 'NewStrongPass123!',
            'new_password2': 'NewStrongPass123!'
        })
        # Form errors, stays on page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'old password is incorrect')

    def test_password_change_mismatch(self):
        """Test changing password with mismatched new passwords."""
        response = self.client.post(self.profile_url, {
            'change_password': '1',
            'old_password': 'TestPass123!',
            'new_password1': 'NewStrongPass123!',
            'new_password2': 'DifferentPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')


class AdminUserManagementTests(TestCase):
    """Test admin user management functionality."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            department='IT'
        )
        self.client.login(email='admin@example.com', password='AdminPass123!')
        self.admin_users_url = reverse('accounts:admin_users')

    def test_admin_users_page_loads(self):
        """Test admin user management page loads."""
        response = self.client.get(self.admin_users_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/user_management.html')

    def test_admin_create_user(self):
        """Test admin creating a new user."""
        response = self.client.post(
            reverse('accounts:admin_user_create'),
            {
                'email': 'newuser@example.com',
                'password': 'NewUser123!',
                'first_name': 'New',
                'last_name': 'User',
                'role': 'AGENT',
                'department': 'IT'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_admin_create_user_duplicate_email(self):
        """Test admin creating user with duplicate email."""
        User.objects.create_user(
            email='existing@example.com',
            password='TestPass123!',
            first_name='Existing',
            last_name='User',
            department='IT'
        )
        response = self.client.post(
            reverse('accounts:admin_user_create'),
            {
                'email': 'existing@example.com',
                'password': 'NewUser123!',
                'first_name': 'New',
                'last_name': 'User',
                'role': 'AGENT',
                'department': 'IT'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_edit_user(self):
        """Test admin editing a user."""
        user = User.objects.create_user(
            email='edit@example.com',
            password='TestPass123!',
            first_name='Old',
            last_name='Name',
            department='IT'
        )
        response = self.client.post(
            reverse('accounts:admin_user_edit', args=[user.pk]),
            {
                'first_name': 'New',
                'last_name': 'Name',
                'role': 'AGENT',
                'department': 'IT',
                'is_active': 'true'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'New')

    def test_admin_toggle_user_active(self):
        """Test admin toggling user active status."""
        user = User.objects.create_user(
            email='toggle@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT'
        )
        response = self.client.post(
            reverse('accounts:admin_user_toggle_active', args=[user.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_admin_cannot_deactivate_self(self):
        """Test admin cannot deactivate their own account."""
        response = self.client.post(
            reverse('accounts:admin_user_toggle_active', args=[self.admin.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_change_password(self):
        """Test admin changing user password."""
        user = User.objects.create_user(
            email='passchange@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            department='IT'
        )
        response = self.client.post(
            reverse('accounts:admin_user_change_password', args=[user.pk]),
            {'password': 'NewStrongPass123!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewStrongPass123!'))