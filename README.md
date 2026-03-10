# Pay Webhooks

Это тестовое приложение, реализующее простой платежный шлюз.

## Что делает приложение

Если совсем просто, приложение делает такой цикл:
1. Магазин отправляет запрос на создание платежа.
2. Приложение проверяет подпись и доступный баланс.
3. Если денег хватает, сумма резервируется.
4. Платеж отправляется во встроенного тестового провайдера.
5. Провайдер отправляет вебхук обратно в приложение.
6. Если платеж успешный, деньги списываются.
7. Если платеж отменен, резерв снимается и деньги не списываются.

## Основные ручки

- `GET /health` — проверка, что сервис запущен.
- `GET /api/v1/me` — профиль мерчанта и его баланс.
- `POST /api/v1/payments` — создать новый платеж.
- `POST /provider/api/v1/payments` — внутренняя ручка тестового провайдера.
- `POST /api/v1/provider/webhook` — внутренняя ручка приема вебхуков от провайдера.

## Статусы платежа

- `Created` — платеж создан внутри приложения.
- `Processing` — платеж отправлен провайдеру.
- `Completed` — платеж успешно завершен, деньги списаны.
- `Canceled` — платеж отменен, деньги не списаны.

## Тестовые учетные данные

Мерчант 1:
- `X-API-Key`: `merchant-demo-token`
- секрет для подписи: `merchant-demo-secret`
- стартовый баланс: `1000.00`

Мерчант 2:
- `X-API-Key`: `merchant-backup-token`
- секрет для подписи: `merchant-backup-secret`
- стартовый баланс: `500.00`

## Запуск проекта

```bash
git clone <repo-url>
cd pay_webhooks
docker-compose up --build
```

Если база осталась после неудачного запуска, начать с чистого состояния:

```bash
docker-compose down -v
docker-compose up --build
```

## Как понять, что сервис запустился

Открыть:
- [http://localhost:8000/health](http://localhost:8000/health)

Ожидаемый ответ:

```json
{"status":"ok"}
```

## Автодокументация

После запуска открыть:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Важно про Swagger

Swagger в этом проекте не умеет сам вычислять `X-Signature`.
Поэтому для быстрого тестирования ниже уже приведены готовые подписи.

## Готовые подписи для методов мерчанта

Ниже перечислены готовые значения для методов, которые вызывает сам мерчант.

### Метод `GET /health`

Для этой ручки подпись не нужна.

### Метод `GET /api/v1/me`

Тело запроса: пустое.

Для мерчанта 1:
- `X-API-Key`: `merchant-demo-token`
- `X-Signature`: `b273c1b53f0e1b2d89a5ddc5e418eb6acb126e7745ee26ea2658bcbe9f0102b1`

Для мерчанта 2:
- `X-API-Key`: `merchant-backup-token`
- `X-Signature`: `9a6fe1439fe6f0461ea7131e51412597cc5cf39aee7b753842377967deaa4309`

### Метод `POST /api/v1/payments`

Ниже 2 готовых тестовых тела запроса.

#### Вариант 1. Успешный платеж

Тело запроса в Swagger:

```json
{
  "external_invoice_id": "demo-1001",
  "amount": "12.34"
}
```

Если в Swagger вставлен JSON именно в таком виде, использовать:

Для мерчанта 1:
- `X-API-Key`: `merchant-demo-token`
- `X-Signature`: `2f36650ef55e4b2fe082f99de1ea945751acec43b85825da257532d1692013f2`

Для мерчанта 2:
- `X-API-Key`: `merchant-backup-token`
- `X-Signature`: `d7d1aceb427e885a8204bada59b71dd4f4b9b5accc2e5c5313024ac669f34592`

#### Вариант 2. Отмененный платеж

Если `external_invoice_id` начинается с `cancel`, тестовый провайдер завершает платеж отменой.

Тело запроса в Swagger:

```json
{
  "external_invoice_id": "cancel-demo-2001",
  "amount": "7.89"
}
```

Если в Swagger вставлен JSON именно в таком виде, использовать:

Для мерчанта 1:
- `X-API-Key`: `merchant-demo-token`
- `X-Signature`: `680f77208786c454bb8f7feb322836fba61c599dd351574dde2c76cb992d86fa`

Для мерчанта 2:
- `X-API-Key`: `merchant-backup-token`
- `X-Signature`: `618998f595b8da2b63f032b672bc21ae0c2be72db8bf8ea9a2941bdc35b8a7b4`

## Какие методы обычному пользователю вызывать не нужно

Ниже ручки, которые существуют внутри сценария работы приложения, но руками обычно не вызываются:
- `POST /provider/api/v1/payments`
- `POST /api/v1/provider/webhook`

## Как быстро протестировать через Swagger

### Сценарий 1. Посмотреть баланс мерчанта

1. Открыть [http://localhost:8000/docs](http://localhost:8000/docs)
2. Найти `GET /api/v1/me`
3. Нажать `Try it out`
4. Для мерчанта 1 вставить:
   - `x-api-key`: `merchant-demo-token`
   - `x-signature`: `b273c1b53f0e1b2d89a5ddc5e418eb6acb126e7745ee26ea2658bcbe9f0102b1`
5. Нажать `Execute`

### Сценарий 2. Создать успешный платеж

1. Найти `POST /api/v1/payments`
2. Нажать `Try it out`
3. Для мерчанта 1 вставить:
   - `x-api-key`: `merchant-demo-token`
   - `x-signature`: `2f36650ef55e4b2fe082f99de1ea945751acec43b85825da257532d1692013f2`
4. Вставить тело:

```json
{
  "external_invoice_id": "demo-1001",
  "amount": "12.34"
}
```

5. Нажать `Execute`
6. Подождать 2-3 секунды
7. Снова вызвать `GET /api/v1/me`

### Сценарий 3. Создать отмененный платеж

1. В той же ручке `POST /api/v1/payments` вставить:
   - `x-api-key`: `merchant-demo-token`
   - `x-signature`: `680f77208786c454bb8f7feb322836fba61c599dd351574dde2c76cb992d86fa`
2. Вставить тело:

```json
{
  "external_invoice_id": "cancel-demo-2001",
  "amount": "7.89"
}
```

3. Нажать `Execute`
4. Подождать 2-3 секунды
5. Снова вызвать `GET /api/v1/me`

## Важно

- Эти подписи подходят только для точно такого же тела запроса.
- Если изменить сумму, `external_invoice_id`, порядок полей или формат JSON, подпись нужно считать заново.
- Если дважды отправить `POST /api/v1/payments` с одним и тем же `external_invoice_id` для одного мерчанта, сервис вернет `409 Conflict`.