from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse

from .forms import NewBoardForm, NewTopicForm, PostForm
from .models import Board, Post, Topic

@login_required
def home(request):
    boards = Board.objects.all()
    return render(request, 'home.html', {'boards': boards})

@login_required
def new_board(request):
    user = request.user
    if request.method == 'POST':
        if str(user) == 'intel66':
            form = NewBoardForm(request.POST)
            if form.is_valid():
                board = form.save(commit=False)
                board.save()
        return redirect('home')
    else:
        form = NewBoardForm()
    return render(request, 'new_board.html', {'form': form, 'user': user})

@login_required
def board_topics(request, pk):
    board = get_object_or_404(Board, pk=pk)
    queryset = board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
    page = request.GET.get('page', 1)

    paginator = Paginator(queryset, 20)

    try:
        topics = paginator.page(page)
    except PageNotAnInteger:
        topics = paginator.page(1)
    except EmptyPage:
        topics = paginator.page(1)

    return render(request, 'topics.html', {'board': board, 'topics': topics})

@login_required
def topic_posts(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    posts = topic.posts.order_by('created_at')
    user = request.user
    if topic.starter != user:
        session_key = 'viewed_topic_{}'.format(topic_pk)
        if request.session.get(session_key,False):
            topic.views += 1
            topic.save()
            request.session[session_key] = True
    return render(request, 'topic_posts.html', {'posts': posts,'topic': topic})


@login_required
def new_topic(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if request.method == 'POST':
        form = NewTopicForm(request.POST)
        if form.is_valid():
            user = request.user
            topic = form.save(commit=False)
            topic.board = board
            topic.starter = user
            topic.save()
            Post.objects.create(
                message = form.cleaned_data['message'],
                topic = topic,
                created_by = user
            )
            return redirect('topic_posts', pk=pk, topic_pk=topic.pk)
    else:
        form = NewTopicForm()
    return render(request, 'new_topic.html', {'board': board, 'form': form})


@login_required
def reply_topic(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user
            post.save()

            topic.last_updated = timezone.now()
            topic.save()

            topic_url = reverse('topic_posts', kwargs={'pk': pk, 'topic_pk': topic_pk})
            topic_post_url = '{url}?page={page}#{id}'.format(
                url=topic_url,
                id=post.pk,
                page=topic.get_page_count()
            )

            return redirect(topic_post_url)

    else:
        form = PostForm()
    return render(request, 'reply_topic.html', {'topic': topic, 'form': form})


@login_required
def edit_post(request, pk, topic_pk, post_pk):
    post = get_object_or_404(Post, topic__board__pk=pk, topic__pk=topic_pk, pk=post_pk)
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    user = request.user
    if request.method == 'POST':
        if post.created_by == user:
            form = PostForm(request.POST)
            if form.is_valid():
                post.message = form.cleaned_data['message']
                post.save()

                topic.last_updated = timezone.now()
                topic.save()

                return redirect('topic_posts', pk=pk, topic_pk=topic_pk)

        return redirect('topic_posts', pk=pk, topic_pk=topic_pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'edit_post.html', {'post':post, 'form': form})

# TODO: Making the following list and only show their posts
# TODO: Have a button to show the replys in ascdening or descening order
# TODO: Implement ElasticSearch
