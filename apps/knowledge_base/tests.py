from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.knowledge_base.models import Article, ArticleVersion, ArticleFeedback
from apps.common.models import Category, Tag

User = get_user_model()


class ArticleModelTests(TestCase):
    """Test Article model."""

    def setUp(self):
        self.author = User.objects.create_user(
            email='author@example.com',
            password='TestPass123!',
            first_name='Author',
            last_name='User',
            department='IT',
            role=User.Role.AGENT,
            is_active=True,
            email_verified=True
        )
        self.category = Category.objects.create(name='IT', slug='it')

    def test_article_creation(self):
        article = Article.objects.create(
            title='Test Article',
            slug='test-article',
            content='Test content',
            author=self.author,
            category=self.category,
            status=Article.Status.DRAFT
        )
        self.assertEqual(article.title, 'Test Article')
        self.assertEqual(article.author, self.author)
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertEqual(str(article), 'Test Article')

    def test_article_slug_auto_generation(self):
        article = Article.objects.create(
            title='Test Article With Spaces',
            content='Test content',
            author=self.author,
            category=self.category
        )
        self.assertTrue(article.slug.startswith('test-article-with-spaces'))

    def test_article_version_creation(self):
        article = Article.objects.create(
            title='Test Article',
            slug='test-article',
            content='Original content',
            author=self.author,
            category=self.category
        )
        version = ArticleVersion.objects.create(
            article=article,
            content='Updated content',
            edited_by=self.author
        )
        self.assertEqual(version.article, article)
        self.assertEqual(version.content, 'Updated content')
        self.assertEqual(version.edited_by, self.author)


class KnowledgeBaseViewTests(TestCase):
    """Test knowledge base views."""

    def setUp(self):
        self.client = Client()
        self.author = User.objects.create_user(
            email='author@example.com',
            password='TestPass123!',
            first_name='Author',
            last_name='User',
            department='IT',
            role=User.Role.AGENT,
            is_active=True,
            email_verified=True
        )
        self.category = Category.objects.create(name='IT', slug='it')
        self.client.login(email='author@example.com', password='TestPass123!')

    def test_kb_management_page_loads(self):
        """Test KB management page loads for authenticated agent."""
        response = self.client.get(reverse('kb:management'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'knowledge_base/management.html')

    def test_article_create(self):
        """Test creating a new article."""
        response = self.client.post(reverse('kb:create'), {
            'title': 'New Article',
            'content': 'New content',
            'category': self.category.id,
            'visibility': 'PUBLIC'
        })
        # Should redirect to management page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Article.objects.filter(title='New Article').exists())

    def test_article_edit(self):
        """Test editing an article."""
        article = Article.objects.create(
            title='Test Article',
            slug='test-article',
            content='Original content',
            author=self.author,
            category=self.category,
            status=Article.Status.DRAFT
        )
        response = self.client.post(reverse('kb:edit', args=[article.pk]), {
            'title': 'Updated Article',
            'content': 'Updated content',
            'category': self.category.id,
            'visibility': 'PUBLIC'
        })
        self.assertEqual(response.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Updated Article')

    def test_kb_portal_loads(self):
        """Test KB portal loads with published articles."""
        Article.objects.create(
            title='Published Article',
            slug='published-article',
            content='Published content',
            author=self.author,
            category=self.category,
            status=Article.Status.PUBLISHED,
            visibility='PUBLIC'
        )
        response = self.client.get(reverse('kb:portal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Published Article')