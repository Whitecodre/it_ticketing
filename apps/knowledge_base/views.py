import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils.text import slugify
from .models import Article, ArticleVersion, Category, ArticleFeedback
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from apps.tickets.models import Ticket


@login_required
def kb_management(request):
    """Agent/TL/Admin view for managing KB articles."""
    user = request.user
    if user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()

    drafts = Article.objects.filter(author=user, status=Article.Status.DRAFT)
    pending_review = Article.objects.filter(status=Article.Status.PENDING_REVIEW) if user.role in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN'] else []
    published = Article.objects.filter(status=Article.Status.PUBLISHED)

    # Choose sidebar based on role
    sidebar_map = {
        'AGENT': 'partials/sidebar_agent.html',
        'TEAM_LEAD': 'partials/sidebar_team_lead.html',
        'ADMIN': 'partials/sidebar_admin.html',
        'SUPERADMIN': 'partials/sidebar_superadmin.html',  
    }
    sidebar_template = sidebar_map.get(user.role, 'partials/sidebar_agent.html')

    context = {
        'drafts': drafts,
        'pending_review': pending_review,
        'published': published,
        'sidebar_template': sidebar_template,
    }
    return render(request, 'knowledge_base/management.html', context)


@login_required
def article_create(request):
    """Create a new article draft."""
    if request.user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        visibility = request.POST.get('visibility', 'INTERNAL')
        slug = slugify(title) + '-' + str(int(time.time()))
        article = Article.objects.create(
            title=title,
            slug=slug,
            content=content,
            category_id=category_id if category_id else None,
            visibility=visibility,
            author=request.user,
            status=Article.Status.DRAFT
        )
        ArticleVersion.objects.create(article=article, content=content, edited_by=request.user)
        return redirect('kb:management')

    categories = Category.objects.all()
    return render(request, 'knowledge_base/article_form.html', {'categories': categories})


@login_required
def article_edit(request, pk):
    """Edit an existing draft (author only)."""
    article = get_object_or_404(Article, pk=pk)
    if request.user != article.author and request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()

    if request.method == 'POST':
        article.title = request.POST.get('title', article.title)
        article.content = request.POST.get('content', article.content)
        article.visibility = request.POST.get('visibility', article.visibility)
        if request.POST.get('category'):
            article.category_id = request.POST.get('category')
        article.save()
        ArticleVersion.objects.create(article=article, content=article.content, edited_by=request.user)
        return redirect('kb:management')

    categories = Category.objects.all()
    return render(request, 'knowledge_base/article_form.html', {'article': article, 'categories': categories})


@login_required
def article_submit_review(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.user != article.author:
        return HttpResponseForbidden()
    article.status = Article.Status.PENDING_REVIEW
    article.save()
    return redirect('kb:management')


@login_required
def article_publish(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()
    article.status = Article.Status.PUBLISHED
    article.save()
    return redirect('kb:management')


@login_required
def article_archive(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()
    article.status = Article.Status.ARCHIVED
    article.save()
    return redirect('kb:management')

@login_required
def kb_portal(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    articles = Article.objects.filter(status=Article.Status.PUBLISHED, visibility='PUBLIC')

    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(content__icontains=query))
    if category_id:
        articles = articles.filter(category_id=category_id)

    categories = Category.objects.annotate(article_count=Count('articles', filter=Q(articles__status=Article.Status.PUBLISHED, articles__visibility='PUBLIC')))

    context = {
        'articles': articles,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
    }
    return render(request, 'knowledge_base/portal.html', context)

@login_required
def kb_article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, status=Article.Status.PUBLISHED, visibility='PUBLIC')
    # Check if user already gave feedback
    user_feedback = None
    if request.user.is_authenticated:
        try:
            user_feedback = ArticleFeedback.objects.get(article=article, user=request.user)
        except ArticleFeedback.DoesNotExist:
            pass
    context = {
        'article': article,
        'user_feedback': user_feedback,
    }
    return render(request, 'knowledge_base/article_detail.html', context)

@login_required
@require_POST
def kb_feedback(request, pk):
    article = get_object_or_404(Article, pk=pk)
    helpful = request.POST.get('helpful') == 'true'
    feedback, created = ArticleFeedback.objects.update_or_create(
        article=article,
        user=request.user,
        defaults={'helpful': helpful}
    )
    helpful_count = article.feedback.filter(helpful=True).count()
    not_helpful_count = article.feedback.filter(helpful=False).count()
    return JsonResponse({
        'status': 'ok',
        'helpful_count': helpful_count,
        'not_helpful_count': not_helpful_count,
    })

@login_required
def convert_ticket_to_kb(request, ticket_pk):
    ticket = get_object_or_404(Ticket, pk=ticket_pk)
    if request.user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()

    # Create draft article from ticket
    title = ticket.title
    content = ticket.description
    slug = slugify(title) + '-' + str(int(time.time()))

    article = Article.objects.create(
        title=title,
        slug=slug,
        content=content,
        visibility='INTERNAL',   # default internal – agent can change
        author=request.user,
        status=Article.Status.DRAFT
    )
    ArticleVersion.objects.create(article=article, content=content, edited_by=request.user)

    return redirect('kb:edit', pk=article.pk)
