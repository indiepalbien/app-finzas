from django.contrib import admin
from .models import Choice, Question


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class QuestionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["question_text"]}),
        ("Date information", {"fields": ["pub_date"], "classes": ["collapse"]}),
    ]
    inlines = [ChoiceInline]
    list_display = ["question_text", "pub_date", "was_published_recently"]
    list_filter = ["pub_date"]
    search_fields = ["question_text"]



admin.site.register(Question, QuestionAdmin)

# Register new finance models
from .models import Category, Project, Payee, Source, Exchange, Balance, Transaction

admin.site.register(Category)
admin.site.register(Project)
admin.site.register(Payee)
admin.site.register(Source)
admin.site.register(Exchange)
admin.site.register(Balance)
admin.site.register(Transaction)