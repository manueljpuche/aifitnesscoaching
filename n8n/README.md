# n8n Workflows — AI Fitness Coaching

## Requisitos Previos

- n8n corriendo en `dev.sabbagradiologos.com` (ya existe)
- Backend API corriendo en el mismo servidor (Docker Compose)
- Bot de Telegram creado vía [@BotFather](https://t.me/BotFather)

---

## Variables de Entorno en n8n

Configura las siguientes variables en **Settings → Variables** (o en el archivo `.env` de n8n):

| Variable | Descripción | Ejemplo |
|---|---|---|
| `BACKEND_URL` | URL interna del backend | `http://localhost:8000` |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | `123456:ABC-DEF1234...` |
| `TELEGRAM_WEBHOOK_SECRET` | Secreto HMAC para verificar webhooks de Telegram | (cadena aleatoria de 32+ chars) |
| `N8N_INTERNAL_SECRET` | Secreto compartido para llamadas internas n8n→backend | (cadena aleatoria de 32+ chars) |
| `ADMIN_TELEGRAM_ID` | Chat ID del admin para alertas | `123456789` |

> **Nota**: `BACKEND_URL` debe ser `http://localhost:8000` si n8n y el backend están en el mismo servidor, o la URL interna de Docker si están en la misma red Docker.

---

## Importar Workflows

1. Abre n8n en `https://dev.sabbagradiologos.com`
2. Ve a **Workflows → Import from File**
3. Importa cada archivo JSON de la carpeta `n8n/workflows/` en orden:

| # | Archivo | Tipo | Descripción |
|---|---|---|---|
| 01 | `01-telegram-webhook.json` | Webhook | Flujo principal: recibe mensajes de Telegram, procesa con IA, responde |
| 02 | `02-daily-meal-reminders.json` | Cron (horario) | Recordatorios de comidas pendientes |
| 03 | `03-daily-plan-delivery.json` | Cron (7:00) | Envío del plan diario por la mañana |
| 04 | `04-weekly-checkin.json` | Cron (Dom 20:00) | Check-in semanal con resumen |
| 05 | `05-challenge-daily-tracking.json` | Cron (22:00) | Seguimiento diario de retos activos |
| 06 | `06-supplement-reminders.json` | Cron (30 min) | Recordatorios de suplementos |
| 07 | `07-sleep-quality-ask.json` | Cron (8:00) | Pregunta de calidad de sueño |
| 08 | `08-pre-post-workout-nutrition.json` | Cron (15 min) | Nutrición pre/post entrenamiento |
| 09 | `09-hydration-streak-reminders.json` | Cron (14:00/18:00 + 21:00) | Hidratación + alerta de racha |
| 10 | `10-progress-photo-reminder.json` | Cron (1º mes) | Foto de progreso mensual |
| 11 | `11-symptom-followup.json` | Cron (30 min) | Seguimiento 3h después de reporte de síntomas |
| 12 | `12-training-phase-transition.json` | Cron (Lun 8:00) | Transición de fase de entrenamiento |
| 13 | `13-data-cleanup.json` | Cron (1º mes 3:00) | Limpieza mensual de datos antiguos |
| 14 | `14-health-check-monitor.json` | Cron (5 min) | Monitor de salud del backend |
| 15 | `15-temporary-restriction-expiry.json` | Cron (00:00) | Expiración de restricciones temporales |
| 16 | `16-recovery-followup.json` | Cron (cada 3 días) | Seguimiento de usuarios en recuperación |

1. **Activa** cada workflow después de importarlo

---

## Configurar Webhook de Telegram

Una vez importado el workflow `01-telegram-webhook.json`, necesitas:

1. Obtener la URL del webhook de n8n (la genera automáticamente el nodo Webhook)
   - Normalmente: `https://dev.sabbagradiologos.com/webhook/telegram`
2. Registrar el webhook con Telegram:

```bash
curl -X POST "https://api.telegram.org/bot<TU_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://dev.sabbagradiologos.com/webhook/telegram",
    "secret_token": "<TU_TELEGRAM_WEBHOOK_SECRET>",
    "allowed_updates": ["message", "callback_query"]
  }'
```

1. Verificar que el webhook está configurado:

```bash
curl "https://api.telegram.org/bot<TU_BOT_TOKEN>/getWebhookInfo"
```

---

## Flujo de Comunicación

```
Telegram → Webhook n8n → Backend API (JWT auth) → n8n → Telegram
                ↑                                      |
                └──────────────────────────────────────┘
```

1. **Telegram** envía update al webhook de n8n
2. **n8n** verifica HMAC, autentica con el backend (`POST /auth/login`)
3. **n8n** descarga archivos si es necesario (voz/foto)
4. **n8n** envía al backend (`POST /ai/message` o `POST /ai/transcribe`)
5. **n8n** recibe respuesta y la envía al usuario via Telegram API

---

## Endpoints del Backend Usados por n8n

### Autenticación

- `POST /api/v1/auth/login` — Login con telegram_id, devuelve JWT

### Procesamiento IA

- `POST /api/v1/ai/message` — Procesar mensaje de texto (requiere JWT)
- `POST /api/v1/ai/transcribe` — Transcribir audio (requiere JWT)
- `POST /api/v1/ai/feedback` — Registrar feedback (requiere JWT)

### Endpoints Batch (Cron Jobs) — Auth: `X-N8N-Secret`

- `GET /api/v1/nutrition/schedule/pending-reminders` — Comidas pendientes
- `GET /api/v1/notifications/daily-plan-batch` — Plan diario para envío
- `POST /api/v1/checkins/weekly-batch` — Generar check-ins semanales
- `POST /api/v1/challenges/daily-progress-batch` — Progreso de retos
- `GET /api/v1/supplements/pending-reminders` — Suplementos pendientes
- `GET /api/v1/notifications/morning-sleep-batch` — Batch calidad de sueño
- `GET /api/v1/notifications/workout-nutrition-batch` — Nutrición pre/post workout
- `GET /api/v1/notifications/hydration-batch` — Usuarios bajo meta de agua
- `GET /api/v1/gamification/streak-risk-batch` — Rachas en riesgo
- `GET /api/v1/notifications/progress-photo-batch` — Fotos de progreso pendientes
- `GET /api/v1/notifications/symptom-followup-batch` — Seguimiento de síntomas
- `POST /api/v1/workouts/phase-transition-batch` — Transiciones de fase
- `POST /api/v1/admin/data-cleanup` — Limpieza de datos
- `POST /api/v1/users/expire-temporary` — Expirar restricciones temporales
- `GET /api/v1/notifications/recovery-followup-batch` — Seguimiento de recuperación
- `GET /health` — Health check (sin auth)

---

## Troubleshooting

### El webhook no recibe mensajes

- Verifica que el webhook está registrado: `getWebhookInfo`
- Asegúrate de que n8n es accesible desde internet en la URL del webhook
- Revisa los logs de n8n para errores de HMAC

### Error de conexión al backend

- Verifica que `BACKEND_URL` apunta correctamente al backend
- Si están en la misma máquina: `http://localhost:8000`
- Si están en la misma red Docker: `http://app:8000`
- Revisa que el backend está corriendo: `docker compose ps`

### Los cron jobs no envían mensajes

- Verifica que los workflows están **activados** (toggle verde)
- Revisa que `N8N_INTERNAL_SECRET` coincide en n8n y en el `.env` del backend
- Revisa los logs de ejecución en n8n para ver errores del backend

### Error 401 en llamadas al backend

- Verifica `N8N_INTERNAL_SECRET` para endpoints batch
- Para endpoints con JWT: el workflow `01` hace login automático, pero verifica que las credenciales del bot están en la DB
