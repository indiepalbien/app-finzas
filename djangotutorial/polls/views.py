# Create your views here.
from django.http import HttpResponse
from django.template import loader
from django.http import Http404
from .models import Question
from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db.models import F
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Category, Project, Payee, Source, Exchange, Balance, Transaction, Choice


@login_required
def manage_dashboard(request):
    """Simple management dashboard with links to each resource."""
    resources = [
        ("Categories", "polls:manage_categories"),
        ("Projects", "polls:manage_projects"),
        ("Payees", "polls:manage_payees"),
        ("Sources", "polls:manage_sources"),
        ("Exchanges", "polls:manage_exchanges"),
        ("Balances", "polls:manage_balances"),
        ("Transactions", "polls:manage_transactions"),
    ]
    return render(request, "manage/dashboard.html", {"resources": resources})


class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return obj.user == self.request.user


class OwnerListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model_name = self.model._meta.model_name
        ctx["create_url_name"] = f"polls:manage_{model_name}_add"
        ctx["edit_url_name"] = f"polls:manage_{model_name}_edit"
        # Provide a safe verbose name for templates (avoid accessing _meta from templates)
        ctx["model_verbose_name_plural"] = self.model._meta.verbose_name_plural
        return ctx


class OwnerCreateView(LoginRequiredMixin, CreateView):
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # provide a safe verbose name for templates
        ctx["model_verbose_name"] = self.model._meta.verbose_name
        return ctx


class OwnerUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["model_verbose_name"] = self.model._meta.verbose_name
        return ctx


# Category views
class CategoryListView(OwnerListView):
    model = Category
    template_name = "manage/list.html"


class CategoryCreateView(OwnerCreateView):
    model = Category
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_categories")


class CategoryUpdateView(OwnerUpdateView):
    model = Category
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_categories")


# Project views
class ProjectListView(OwnerListView):
    model = Project
    template_name = "manage/list.html"


class ProjectCreateView(OwnerCreateView):
    model = Project
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_projects")


class ProjectUpdateView(OwnerUpdateView):
    model = Project
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_projects")


# Payee views
class PayeeListView(OwnerListView):
    model = Payee
    template_name = "manage/list.html"


class PayeeCreateView(OwnerCreateView):
    model = Payee
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_payees")


class PayeeUpdateView(OwnerUpdateView):
    model = Payee
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_payees")


# Source views
class SourceListView(OwnerListView):
    model = Source
    template_name = "manage/list.html"


class SourceCreateView(OwnerCreateView):
    model = Source
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_sources")


class SourceUpdateView(OwnerUpdateView):
    model = Source
    fields = ["name"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_sources")


# Exchange views
class ExchangeListView(OwnerListView):
    model = Exchange
    template_name = "manage/list.html"


class ExchangeCreateView(OwnerCreateView):
    model = Exchange
    fields = ["date", "source_currency", "target_currency", "rate"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_exchanges")


class ExchangeUpdateView(OwnerUpdateView):
    model = Exchange
    fields = ["date", "source_currency", "target_currency", "rate"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_exchanges")


# Balance views
class BalanceListView(OwnerListView):
    model = Balance
    template_name = "manage/list.html"


class BalanceCreateView(OwnerCreateView):
    model = Balance
    fields = ["source", "start_date", "end_date", "currency", "amount"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_balances")


class BalanceUpdateView(OwnerUpdateView):
    model = Balance
    fields = ["source", "start_date", "end_date", "currency", "amount"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_balances")


# Transaction views
class TransactionListView(OwnerListView):
    model = Transaction
    template_name = "manage/list.html"


class TransactionCreateView(OwnerCreateView):
    model = Transaction
    fields = ["date", "amount", "currency", "source", "category", "project", "payee", "comments"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_transactions")


class TransactionUpdateView(OwnerUpdateView):
    model = Transaction
    fields = ["date", "amount", "currency", "source", "category", "project", "payee", "comments"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_transactions")

class IndexView(generic.ListView):
    template_name = "polls/index.html"
    context_object_name = "latest_question_list"

    def get_queryset(self):
        """
        Return the last five published questions (not including those set to be
        published in the future).
        """
        return Question.objects.filter(pub_date__lte=timezone.now()).order_by("-pub_date")[
            :5
        ]

class DetailView(generic.DetailView):
    model = Question
    template_name = "polls/detail.html"


class ResultsView(generic.DetailView):
    model = Question
    template_name = "polls/results.html"

def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(
            request,
            "polls/detail.html",
            {
                "question": question,
                "error_message": "You didn't select a choice.",
            },
        )
    else:
        selected_choice.votes = F("votes") + 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse("polls:results", args=(question.id,)))


def register(request):
    """Minimal user registration view using Django's `UserCreationForm`.

    - Uses built-in form for username/password validation.
    - Redirects to the login page after successful registration.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada. Por favor, ingresá.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def landing(request):
    """Simple landing page at root ('/')."""
    return render(request, 'landing.html')


@login_required
def profile(request):
    """Simple profile page showing username."""
    return render(request, 'profile.html', {'user': request.user})