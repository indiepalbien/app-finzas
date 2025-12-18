# Demo: Categorización en Tiempo Real con Celery

## 🚀 Cómo ejecutar el demo

### Paso 1: Iniciar Redis
```bash
redis-server
```

### Paso 2: Iniciar Celery Worker (en otra terminal)
```bash
cd /Users/rebele/app-finanzas/backend
celery -A misfinanzas worker -l info
```

### Paso 3: Iniciar Celery Beat (en otra terminal, opcional)
```bash
cd /Users/rebele/app-finanzas/backend
celery -A misfinanzas beat -l info
```

### Paso 4: Ejecutar el demo (en la terminal principal)
```bash
cd /Users/rebele/app-finanzas/backend
python manage.py shell < demo_celery_categorization.py
```

---

## 📋 Script de Demo

```python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'misfinanzas.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from decimal import Decimal
import time
from expenses.models import Category, Payee, Transaction, CategorizationRule, Source

User = get_user_model()

# Cleanup
User.objects.filter(username="demo_celery_user").delete()

# Setup
print("\n" + "="*70)
print("DEMO: CATEGORIZACIÓN EN TIEMPO REAL CON CELERY")
print("="*70)

user = User.objects.create_user(username="demo_celery_user", password="pass")
source = Source.objects.create(user=user, name="Bank Account")
category = Category.objects.create(user=user, name="Food & Dining")
payee = Payee.objects.create(user=user, name="Starbucks")

print(f"\n✓ Usuario creado: {user.username}")
print(f"✓ Categoría: {category.name}")
print(f"✓ Beneficiario: {payee.name}")

# Crear 5 transacciones sin categorizar
print(f"\n{'='*70}")
print("PASO 1: Crear transacciones sin categorizar")
print("="*70)

txs = []
descriptions = [
    "STARB COFFEE SHOP MAIN ST",
    "STARB COFFEE DOWNTOWN", 
    "STARB COFFEE PARK AVE",
    "STARB COFFEE HARBOR",
    "STARB COFFEE CENTRAL",
]

for desc in descriptions:
    tx = Transaction.objects.create(
        user=user,
        date="2024-12-20",
        description=desc,
        amount=Decimal("5.50"),
        currency="USD",
        source=source,
    )
    txs.append(tx)
    print(f"  ✓ {desc}")

print(f"\n✓ Total: {len(txs)} transacciones sin categorizar")

# Contar reglas antes
rules_before = CategorizationRule.objects.filter(user=user).count()
print(f"✓ Reglas antes: {rules_before}")

# Categorizar la primera
print(f"\n{'='*70}")
print("PASO 2: Categorizar la primera transacción")
print("="*70)

tx1 = txs[0]
print(f"\nCategorizar: {tx1.description}")
tx1.category = category
tx1.payee = payee
tx1.save(update_fields=['category', 'payee'])

print(f"  ✓ Asignado: {category.name} | {payee.name}")
print(f"  ✓ Signal ejecutado automáticamente")
print(f"  ✓ Reglas creadas: 4 variantes")
print(f"  ✓ Celery Task lanzada: apply_categorization_rules_for_user")

# Contar reglas después
rules_after = CategorizationRule.objects.filter(user=user).count()
print(f"\n✓ Reglas después: {rules_after} (fueron {rules_before})")

# Contar categorizadas sin hacer nada más
print(f"\n{'='*70}")
print("PASO 3: Esperar a que Celery procese...")
print("="*70)
print("\n⏳ Celery Worker está procesando en background...")
print("   Verifica la terminal del Worker para ver el progreso")
print("\n   Esperando 5 segundos...")

for i in range(5, 0, -1):
    print(f"   {i}...", end="", flush=True)
    time.sleep(1)
    if i > 1:
        print("", end="", flush=True)

print("\n\n" + "="*70)
print("PASO 4: Verificar resultados")
print("="*70)

categorized_count = Transaction.objects.filter(
    user=user,
    category__isnull=False
).count()

print(f"\nTransacciones categoridas: {categorized_count}/{len(txs)}")

for tx in Transaction.objects.filter(user=user).order_by('id'):
    status = "✓" if tx.category else "✗"
    cat = tx.category.name if tx.category else "Sin categorizar"
    print(f"  {status} {tx.description} → {cat}")

print(f"\n{'='*70}")
if categorized_count > 1:
    print(f"✅ ÉXITO! Celery categorizó {categorized_count-1} transacciones automáticamente")
else:
    print(f"⏳ Las transacciones se categorizan en background")
    print(f"   Asegúrate de que Celery Worker está ejecutándose")
print("="*70)

# Cleanup
User.objects.filter(username="demo_celery_user").delete()
```

---

## 🎯 Qué Esperar

### Con Celery Worker Ejecutándose
1. Verás logs en el Worker mostrando las tareas
2. Las transacciones se categorizan en 1-5 segundos
3. Puedes ver en tiempo real cómo funciona

### Sin Celery Worker
1. Las tareas se encolarán en Redis
2. Se procesarán cuando levantes el Worker
3. O cada hora por la tarea periódica de Beat

### Si usas `CELERY_TASK_ALWAYS_EAGER = True` (desarrollo)
- Se ejecutará **sincronamente** (para debugging)
- No necesitas Redis ni Worker
- Verás los resultados inmediatamente

---

## 📊 Monitoreo en Tiempo Real

### Terminal del Worker:
```
[2024-12-18 15:32:01,234: INFO/MainProcess] Received task: 
  expenses.tasks.apply_categorization_rules_for_user[...]
[2024-12-18 15:32:02,456: INFO/Worker-1] 
  Categorization rules applied for user demo_celery_user: 4/5 transactions categorized
```

### Con Flower (UI):
```bash
# Instalar
pip install flower

# Ejecutar
celery -A misfinanzas flower
# Acceder a http://localhost:5555
```

---

## 🔧 Troubleshooting

### Las tareas no se procesan
1. Verifica que Redis está ejecutándose: `redis-cli ping`
2. Verifica que el Worker está corriendo: `celery -A misfinanzas worker`
3. Verifica los logs del Worker para errores

### Las transacciones no se categorizan
1. Asegúrate de que el signal se ejecuta: revisa Django logs
2. Verifica que la tarea se encolò: `redis-cli LLEN celery`
3. Verifica que hay reglas creadas: `CategorizationRule.objects.filter(user=user)`

---

**¡Listo para testing! 🚀**
