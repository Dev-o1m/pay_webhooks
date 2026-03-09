# Pay Webhooks

Асинхронный платежный шлюз на FastAPI, который принимает заявки мерчантов, резервирует баланс, отправляет запрос во встроенного провайдера и обрабатывает его вебхуки.

## Что реализовано
- `GET /api/v1/me` возвращает профиль мерчанта и баланс.
- `POST /api/v1/payments` создает платеж, резервирует сумму и запускает отправку провайдеру с задержкой 1-2 секунды.
- `POST /provider/api/v1/payments` имитирует внешнего провайдера.
- `POST /api/v1/provider/webhook` принимает вебхуки провайдера и финализирует платеж.
- Первый запуск контейнера прогоняет Alembic-миграцию и создает тестовых мерчантов.

## Тестовые данные
- Merchant 1:
  - API token: `merchant-demo-token`
  - API secret: `merchant-demo-secret`
  - Balance: `1000.00`
- Merchant 2:
  - API token: `merchant-backup-token`
  - API secret: `merchant-backup-secret`
  - Balance: `500.00`

## Аутентификация
Используются заголовки:
- `X-API-Key`: токен мерчанта
- `X-Signature`: `HMAC-SHA256(body, api_secret)` в hex

Для `GET /api/v1/me` подпись считается от пустого тела.

Пример подписи на Python:

```python
import hashlib
import hmac

body = b'{"external_invoice_id":"order-1","amount":"10.00"}'
secret = 'merchant-demo-secret'
signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
print(signature)
```

## Запуск

```bash
git clone <repo>
cd pay_webhooks
docker compose up --build
```

После запуска сервис доступен на [http://localhost:8000](http://localhost:8000).

## Запуск тестов

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
```

Для Windows PowerShell активация окружения:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Примеры запросов

`GET /api/v1/me`

```bash
curl -X GET http://localhost:8000/api/v1/me \
  -H "X-API-Key: merchant-demo-token" \
  -H "X-Signature: <signature-for-empty-body>"
```

`POST /api/v1/payments`

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: merchant-demo-token" \
  -H "X-Signature: <signature>" \
  -d '{"external_invoice_id":"order-1","amount":"10.00"}'
```
