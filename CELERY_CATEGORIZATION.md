# Categorización Inteligente en Tiempo Real con Celery

## 🚀 Cómo Funciona Ahora

### Flujo Automático en Tiempo Real

```
1. Usuario categoriza una transacción
         ↓
2. Signal captura el cambio (instantáneo)
         ↓
3. Crea 4 variantes de reglas (instantáneo)
         ↓
4. Lanza tarea Celery (asincrónica, no bloquea)
         ↓
5. Celery Worker procesa hasta 50 transacciones sin categorizar
         ↓
6. Las transacciones similares se categorizan automáticamente
```

## ⚡ Timing

| Evento | Timing | Tecnología |
|--------|--------|-----------|
| Usuario categoriza | Instantáneo | Django Signal |
| Se crean reglas | Instantáneo | Sincrónico en signal |
| Se lanzan tareas | Instantáneo | Celery .delay() |
| Se aplican reglas | 1-5 segundos (típico) | Celery Worker (async) |
| Usuario ve resultados | Al refrescar | Depende del usuario |

## 🔄 Flujo Completo

### Ejemplo Real:

```
15:32:00 - Usuario categoriza "STARB COFFEE" → "Food & Dining"
          ↓ Signal ejecuta inmediatamente
          ✓ Crea 4 variantes de reglas
          ✓ Lanza: apply_categorization_rules_for_user.delay(user_id=5)
          
15:32:01 - Celery Worker recibe la tarea
          ↓ Ejecuta en background
          ✓ Busca transacciones sin categorizar que coincidan
          ✓ Encuentra: "STARB COFFEE PARK", "STARB COFFEE SHOP"
          ✓ Las categoriza automáticamente como "Food & Dining"
          
15:32:03 - Listo! (típicamente en < 5 segundos)
          Si el usuario recarga la página, verá las categorías
```

## 🛠️ Configuración

### En `settings.py`:
```python
CELERY_BEAT_SCHEDULE = {
    'apply-categorization-rules-hourly': {
        'task': 'expenses.tasks.apply_categorization_rules_all_users',
        'schedule': crontab(minute=0),  # Cada hora en background
        'kwargs': {'max_transactions_per_user': 100}
    },
}
```

### En `signals.py`:
```python
# Cuando se categoriza, inmediatamente aplica a 50 transacciones
apply_categorization_rules_for_user.delay(
    user_id=instance.user.id,
    max_transactions=50
)
```

## 📋 Transacciones Procesadas

### Por Categorización (Inmediato)
- Cuando el usuario categoriza → se procesan hasta **50 transacciones**
- No bloquea la respuesta del usuario
- Se ejecuta en background

### Por Horario (Batch)
- Cada hora → se procesan hasta **100 transacciones por usuario**
- Limpia cualquier transacción que se haya pasado
- Configurable en `settings.py`

## 🔧 Ver Tareas en Ejecución

### Con Redis:
```bash
# Conectar a Redis
redis-cli

# Ver colas
LLEN celery
LRANGE celery 0 -1

# Ver tasks en progreso
KEYS celery-task-meta-*
```

### Con Celery:
```bash
# En otra terminal, ejecutar worker para ver logs
celery -A misfinanzas worker -l info

# En otra terminal, ejecutar beat para ver scheduler
celery -A misfinanzas beat -l info
```

## 📊 Monitoreo

### Ver tasks completadas:
```python
from expenses.tasks import apply_categorization_rules_for_user
from celery.result import AsyncResult

# Obtener resultado de una tarea
task = AsyncResult('task-id')
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE
print(task.result)  # Resultado
```

### Ver en logs:
```
[tasks] INFO: Categorization rules applied for user alice: 3/10 transactions categorized
[tasks] INFO: Starting categorization rules for 5 users
```

## 🎯 Ventajas

✅ **Sin bloqueo**: La respuesta del usuario es instantánea  
✅ **Automático**: No requiere acción del usuario  
✅ **Escalable**: Celery maneja muchas tareas en paralelo  
✅ **Fallsafe**: Si falla, se reintentan automáticamente  
✅ **Monitoriable**: Puedes ver el progreso de las tareas  

## ⚠️ Requisitos

Para que funcione necesitas:

1. **Redis** ejecutándose
   ```bash
   redis-server
   ```

2. **Celery Worker** ejecutándose
   ```bash
   celery -A misfinanzas worker -l info
   ```

3. **Celery Beat** ejecutándose (para tareas periódicas)
   ```bash
   celery -A misfinanzas beat -l info
   ```

Si no tienes estos servicios, puedes:
- En **desarrollo**: Usar `CELERY_TASK_ALWAYS_EAGER = True` en settings para ejecutar síncronamente
- En **producción**: Configurar Redis y workers en Docker/Railway

## 📈 Escalabilidad

### Con un worker:
- ~5-10 transacciones por segundo
- Puede procesar cientos de tareas en paralelo

### Con múltiples workers:
```bash
# Worker 1 - procesa tasks de categorización
celery -A misfinanzas worker -Q categorization -l info

# Worker 2 - procesa tasks de email
celery -A misfinanzas worker -Q email -l info

# Worker 3 - procesa tasks de splitwise
celery -A misfinanzas worker -Q splitwise -l info
```

## 🔍 Debugging

### Desactivar ejecución async (solo desarrollo):
```python
# En settings_dev.py
CELERY_TASK_ALWAYS_EAGER = True  # Ejecuta síncronamente para debugging
```

### Ver tasks fallidas:
```python
from celery.result import AsyncResult

# Encontrar task fallida
task = AsyncResult('task-id')
if task.failed():
    print(task.traceback)
```

---

**Resultado: Categorización inteligente completamente automática en tiempo real! 🎉**
