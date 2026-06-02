import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils.text import slugify
from .models import Article, ArticleVersion, Category


@login_required
def kb_management(request):
    """Agent/TL/Admin view for managing KB articles."""
    user = request.user
    if user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponseForbidden()

    drafts = Article.objects.filter(author=user, status=Article.Status.DRAFT)
    pending_review = Article.objects.filter(status=Article.Status.PENDING_REVIEW) if user.role in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN'] else []
    published = Article.objects.filter(status=Article.Status.PUBLISHED)

    context = {
        'drafts': drafts,
        'pending_review': pending_review,
        'published': published,
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