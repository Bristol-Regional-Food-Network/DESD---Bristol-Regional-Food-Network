from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from users.decorators import role_required
from .forms import FarmStoryForm, RecipeForm
from .models import FarmStory, Recipe, SavedRecipe


# ══════════════════════════════════════════════════════════════
#  PRODUCER VIEWS
# ══════════════════════════════════════════════════════════════

@login_required
@role_required('producer')
def content_dashboard(request):
    producer = getattr(request.user, 'producer', None)
    if not producer:
        messages.error(request, 'Producer profile not found.')
        return redirect('producers:producer_dashboard')

    recipes = Recipe.objects.filter(producer=producer)
    stories = FarmStory.objects.filter(producer=producer)

    return render(request, 'content/dashboard.html', {
        'producer': producer,
        'recipes': recipes,
        'stories': stories,
    })


@login_required
@role_required('producer')
def add_recipe(request):
    producer = getattr(request.user, 'producer', None)
    if not producer:
        messages.error(request, 'Producer profile not found.')
        return redirect('producers:producer_dashboard')

    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, producer=producer)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.producer = producer
            recipe.save()
            form.save_m2m()
            messages.success(request, f'Recipe "{recipe.title}" saved successfully.')
            return redirect('content:content_dashboard')
    else:
        form = RecipeForm(producer=producer)

    return render(request, 'content/recipe_form.html', {
        'form': form,
        'producer': producer,
        'action': 'Add',
    })


@login_required
@role_required('producer')
def edit_recipe(request, recipe_id):
    producer = getattr(request.user, 'producer', None)
    recipe = get_object_or_404(Recipe, id=recipe_id, producer=producer)

    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe, producer=producer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Recipe "{recipe.title}" updated.')
            return redirect('content:content_dashboard')
    else:
        form = RecipeForm(instance=recipe, producer=producer)

    return render(request, 'content/recipe_form.html', {
        'form': form,
        'producer': producer,
        'recipe': recipe,
        'action': 'Edit',
    })


@login_required
@role_required('producer')
def delete_recipe(request, recipe_id):
    producer = getattr(request.user, 'producer', None)
    recipe = get_object_or_404(Recipe, id=recipe_id, producer=producer)
    if request.method == 'POST':
        recipe.delete()
        messages.success(request, 'Recipe deleted.')
    return redirect('content:content_dashboard')


@login_required
@role_required('producer')
def add_story(request):
    producer = getattr(request.user, 'producer', None)
    if not producer:
        messages.error(request, 'Producer profile not found.')
        return redirect('producers:producer_dashboard')

    if request.method == 'POST':
        form = FarmStoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.producer = producer
            story.save()
            messages.success(request, f'Story "{story.title}" saved successfully.')
            return redirect('content:content_dashboard')
    else:
        form = FarmStoryForm()

    return render(request, 'content/story_form.html', {
        'form': form,
        'producer': producer,
        'action': 'Add',
    })


@login_required
@role_required('producer')
def edit_story(request, story_id):
    producer = getattr(request.user, 'producer', None)
    story = get_object_or_404(FarmStory, id=story_id, producer=producer)

    if request.method == 'POST':
        form = FarmStoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, f'Story "{story.title}" updated.')
            return redirect('content:content_dashboard')
    else:
        form = FarmStoryForm(instance=story)

    return render(request, 'content/story_form.html', {
        'form': form,
        'producer': producer,
        'story': story,
        'action': 'Edit',
    })


@login_required
@role_required('producer')
def delete_story(request, story_id):
    producer = getattr(request.user, 'producer', None)
    story = get_object_or_404(FarmStory, id=story_id, producer=producer)
    if request.method == 'POST':
        story.delete()
        messages.success(request, 'Story deleted.')
    return redirect('content:content_dashboard')


# ══════════════════════════════════════════════════════════════
#  CUSTOMER / PUBLIC VIEWS
# ══════════════════════════════════════════════════════════════

def recipe_detail(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id, is_published=True)
    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedRecipe.objects.filter(user=request.user, recipe=recipe).exists()
    return render(request, 'content/recipe_detail.html', {
        'recipe': recipe,
        'is_saved': is_saved,
    })


def producer_stories(request, producer_id):
    from producers.models import Producer
    producer = get_object_or_404(Producer, id=producer_id)
    stories = FarmStory.objects.filter(producer=producer, is_published=True)
    recipes = Recipe.objects.filter(producer=producer, is_published=True)
    return render(request, 'content/producer_content.html', {
        'producer': producer,
        'stories': stories,
        'recipes': recipes,
    })


@login_required
def save_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id, is_published=True)
    obj, created = SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    if created:
        messages.success(request, f'"{recipe.title}" saved to your recipes.')
    else:
        messages.info(request, 'You have already saved this recipe.')
    return redirect('content:recipe_detail', recipe_id=recipe_id)


@login_required
def unsave_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    SavedRecipe.objects.filter(user=request.user, recipe=recipe).delete()
    messages.success(request, f'"{recipe.title}" removed from saved recipes.')
    return redirect('content:recipe_detail', recipe_id=recipe_id)


@login_required
def saved_recipes(request):
    saves = SavedRecipe.objects.filter(user=request.user).select_related('recipe__producer')
    return render(request, 'content/saved_recipes.html', {'saves': saves})