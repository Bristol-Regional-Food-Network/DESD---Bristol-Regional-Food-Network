from django import forms
from .models import Recipe, FarmStory


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'ingredients', 'instructions', 'image', 'linked_products', 'seasonal_tag', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Roasted Root Vegetable Medley'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description of the recipe...'}),
            'ingredients': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Enter each ingredient on a new line:\n2 large carrots\n1 parsnip\n3 potatoes'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Enter each step on a new line:\nPreheat oven to 200°C\nPeel and chop vegetables...'}),
            'seasonal_tag': forms.Select(attrs={'class': 'form-select'}),
            'linked_products': forms.CheckboxSelectMultiple(),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, producer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producer:
            self.fields['linked_products'].queryset = producer.products.all().order_by('name')
        self.fields['linked_products'].required = False
        self.fields['image'].required = False


class FarmStoryForm(forms.ModelForm):
    class Meta:
        model = FarmStory
        fields = ['title', 'content', 'image', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Harvest Season at Green Valley Farm'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Share your farm story...'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False
