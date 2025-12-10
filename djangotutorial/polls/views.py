# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.template import loader
from .models import Question
from django.shortcuts import get_object_or_404, render, redirect
from django.views import generic
from django.urls import reverse
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Category, Project, Payee, Source, Exchange, Balance, Transaction, Choice
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone as dj_timezone
from decimal import Decimal, InvalidOperation
import datetime

@login_required
@require_POST
def quick_transaction(request):
    """Handle small inline form to create a Transaction quickly.

    Behavior:
    - Required: description, amount, date, currency.
    - Shows existing DB options in the form (via datalist); on submit, missing related objects are created for the user (cascade).
    - Returns JSON when request is AJAX/JSON (used by inline JS) or redirects with messages for normal POST.
    """
    user = request.user
    data = request.POST

    # Required fields
    description = (data.get("description") or "").strip()
    amount = data.get("amount")
    date_str = data.get("date")
    currency = (data.get("currency") or "").upper().strip()

    # Optional fields: category, project, payee, source
    def get_or_create_model(model, name):
        if not name:
            return None
        obj = model.objects.filter(user=user, name__iexact=name.strip()).first()
        if obj:
            return obj
        return model.objects.create(user=user, name=name.strip())

    category_name = data.get("category")
    project_name = data.get("project")
    payee_name = data.get("payee")
    source_name = data.get("source")

    # Validate required fields
    errors = []
    if not description:
        errors.append("Descripción requerida.")
    if not amount:
        errors.append("Amount is required.")
    if not date_str:
        errors.append("Date is required.")
    if not currency:
        errors.append("Currency is required.")

    # Validate currency format (ISO-4217 style: 3 letters)
    if currency and (len(currency) != 3 or not currency.isalpha()):
        errors.append("Currency must be a 3-letter code (ISO-4217).")

    # If any errors, respond appropriately
    if errors:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.META.get("HTTP_ACCEPT", "").find("application/json") != -1:
            return JsonResponse({"success": False, "errors": errors}, status=400)
        for e in errors:
            messages.error(request, e)
        return redirect("profile")

    # Parse amount and date
    try:
        amount_dec = Decimal(amount)
    except (InvalidOperation, TypeError):
        msg = "Amount must be a number."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": [msg]}, status=400)
        messages.error(request, msg)
        return redirect("profile")

    try:
        tx_date = datetime.date.fromisoformat(date_str)
    except Exception:
        msg = "Invalid date format. Use YYYY-MM-DD."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": [msg]}, status=400)
        messages.error(request, msg)
        return redirect("profile")

    # Create or get related objects (cascade)
    category = get_or_create_model(Category, category_name)
    project = get_or_create_model(Project, project_name)
    payee = get_or_create_model(Payee, payee_name)
    source = get_or_create_model(Source, source_name)

    comments = data.get("comments", "")

    try:
        tx = Transaction.objects.create(
            user=user,
            date=tx_date,
            description=description,
            amount=amount_dec,
            currency=currency,
            source=source,
            category=category,
            project=project,
            payee=payee,
            comments=comments,
        )
        success_msg = "Transacción añadida."
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.META.get("HTTP_ACCEPT", "").find("application/json") != -1:
            return JsonResponse({"success": True, "message": success_msg, "id": tx.id})
        messages.success(request, success_msg)
    except Exception as e:
        err = f"Error creando transacción: {e}"
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": [err]}, status=500)
        messages.error(request, err)

    return redirect("profile")


@login_required
@require_GET
def suggest(request, kind):
    """Return a JSON list of existing names for `kind`.

    `kind` is one of: category, project, payee
    Query param `q` filters by prefix (case-insensitive).
    Only returns existing DB entries (does not create).
    """
    q = request.GET.get("q", "").strip()
    mapping = {
        "category": Category,
        "project": Project,
        "payee": Payee,
        "source": Source,
    }
    Model = mapping.get(kind)
    if not Model:
        return JsonResponse({"results": []})
    qs = Model.objects.filter(user=request.user)
    if q:
        qs = qs.filter(name__istartswith=q)
    names = list(qs.order_by("name").values_list("name", flat=True)[:25])
    return JsonResponse({"results": names})


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
    fields = ["date", "description", "amount", "currency", "source", "category", "project", "payee", "comments"]
    template_name = "manage/form.html"
    success_url = reverse_lazy("polls:manage_transactions")


class TransactionUpdateView(OwnerUpdateView):
    model = Transaction
    fields = ["date", "description", "amount", "currency", "source", "category", "project", "payee", "comments"]
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
    # Provide user's existing options server-side so the profile quick-add doesn't depend on JS timing
    user = request.user
    categories = Category.objects.filter(user=user).order_by('name').values_list('name', flat=True)
    projects = Project.objects.filter(user=user).order_by('name').values_list('name', flat=True)
    payees = Payee.objects.filter(user=user).order_by('name').values_list('name', flat=True)
    sources = Source.objects.filter(user=user).order_by('name').values_list('name', flat=True)
    context = {
        'user': user,
        'qa_categories': list(categories),
        'qa_projects': list(projects),
        'qa_payees': list(payees),
        'qa_sources': list(sources),
    }
    return render(request, 'profile.html', context)