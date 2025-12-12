from django.contrib import admin
from .models import Category, Project, Payee, Source, Exchange, Balance, Transaction

# Register finance models
admin.site.register(Category)
admin.site.register(Project)
admin.site.register(Payee)
admin.site.register(Source)
admin.site.register(Exchange)
admin.site.register(Balance)
admin.site.register(Transaction)