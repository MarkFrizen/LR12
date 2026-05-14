# Отчёт по code review сгенерированного кода

**Дата:** 14.05.2026
**Проект:** Платформа маркетплейса (FastAPI + PostgreSQL)
**Задание 2:** Code review сгенерированного ИИ кода

---

## Проблема 1: Мёртвый импорт — модуль `app/logger.py` не существует

### Что сгенерировал ИИ
ИИ сгенерировал 7 файлов, которые импортируют `from app.logger import get_logger` (и/или `setup_logging`), но сам файл `app/logger.py` **не был создан**:

```python
# app/main.py — строка 1
from app.logger import get_logger, setup_logging

# app/auth/service.py — строка 5
from app.logger import get_logger

# app/services/seller_service.py — строка 8
from app.logger import get_logger
# ... и ещё 4 сервиса
```

### В чём проблема
При запуске приложения возникает `ImportError: cannot import name 'get_logger' from 'app.logger'`. Приложение не стартует — 0% работоспособности. Файл `app/logger.py` физически отсутствует в репозитории.

### Как исправил
Создан файл `app/logger.py` с настройкой логирования (вывод в stdout + ротация файлов в `logs/app.log`):

```python
"""
Модуль настройки логирования приложения.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    # ... настройка handlers, formatters, уровней

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

---

## Проблема 2: Отсутствие аутентификации на CRUD-эндпоинтах

### Что сгенерировал ИИ
Все ~20 эндпоинтов в 5 роутерах (sellers, products, orders, reviews, commissions) не имели `Depends(get_current_user)`:

```python
# app/routers/orders.py (исходная версия)
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    await service.delete(order_id)  # ← любой может удалить любой заказ
```

### В чём проблема
Любой пользователь (включая неавторизованного) может создавать, читать, изменять и удалять любые данные. Полное отсутствие авторизации (CWE-862). Для маркетплейса это означает:
- Любой может удалить чужой товар
- Любой может создать заказ от чужого имени
- Любой может просмотреть все комиссии

### Как исправил
На все эндпоинты добавлены зависимости `Depends(get_current_user)` и ролевые проверки. Итоговая матрица защиты:

| Роутер | POST | GET | PATCH | DELETE |
|---|---|---|---|---|
| sellers | `get_current_user` | `get_current_user` | `get_current_user` | `require_admin` |
| products | `require_seller` | публичный | `require_seller` | `require_admin` |
| orders | `require_buyer` | `get_current_user` | `require_moderator` | `require_admin` |
| reviews | `require_buyer` | публичный | `get_current_user` | `get_current_user` |
| commissions | `require_admin` | `get_current_user` | `require_admin` | `require_admin` |

---

## Проблема 3: JWT-секрет зашит в исходный код

### Что сгенерировал ИИ
```python
# app/auth/config.py (исходная версия)
class AuthSettings(Settings):
    jwt_secret_key: str = "super-secret-key-change-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
```

### В чём проблема
Секретный ключ подписи JWT-токенов хранится в открытом виде в коде (CWE-798). Любой, кто получил доступ к репозиторию, может:
- Подделывать JWT-токены от имени сервера
- Выдавать себя за любого пользователя
- Получить полный доступ к API

### Как исправил
Ключ вынесен в переменную окружения `MP_JWT_SECRET`:

```python
# app/auth/config.py (исправленная версия)
class AuthSettings(Settings):
    jwt_secret_key: str = Field(default="", alias="MP_JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    bcrypt_rounds: int = 12

    def validate_secrets(self) -> None:
        if not self.jwt_secret_key:
            raise RuntimeError("MP_JWT_SECRET не задан!")
```

Добавлен `.env.example` с инструкцией и валидация при старте приложения.

---

## Проблема 4: Пароль базы данных зашит в код

### Что сгенерировал ИИ
```python
# app/config.py (исходная версия)
class Settings(BaseSettings):
    db_password: str = "12345"
```

### В чём проблема
Пароль от PostgreSQL (суперпользователя) зашит в исходном коде (CWE-798). При публикации репозитория пароль становится общедоступным. Злоумышленник может:
- Подключиться напрямую к БД
- Прочитать/изменить/удалить все данные

### Как исправил
Пароль вынесен в `.env` через переменную `MP_DB_PASSWORD`:

```python
# app/config.py (исправленная версия)
class Settings(BaseSettings):
    db_password: str = ""
    # ...

    def validate_db_password(self) -> None:
        if not self.db_password and self.db_user != "postgres":
            raise RuntimeError("MP_DB_PASSWORD не задан!")
```

---

## Проблема 5: CORS `allow_origins=["*"]`

### Что сгенерировал ИИ
```python
# app/main.py (исходная версия)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← любой источник
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### В чём проблема
CORS `allow_origins=["*"]` разрешает запросы с любого домена (CWE-942). Любой внешний сайт может отправлять AJAX-запросы к API маркетплейса от имени браузера пользователя. При `allow_credentials=True` это позволяет:
- Выполнять запросы от имени авторизованного пользователя (CSRF-подобная атака)
- Красть данные через межсайтовые запросы

### Как исправил
Ограничен список разрешённых источников через настройки:

```python
# app/config.py
class Settings(BaseSettings):
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origin_list,
    # ...
)
```

---

## Проблема 6: Отсутствие rate limiting на `/login` и `/register`

### Что сгенерировал ИИ
ИИ не добавил никаких ограничений на частоту запросов к эндпоинтам аутентификации:

```python
# app/auth/router.py (исходная версия)
@router.post("/login")
async def login(data: UserLogin, ...):
    return await auth_service.authenticate(...)
# ← нет лимита запросов
```

### В чём проблема
Атакующий может выполнять неограниченное количество попыток подбора пароля (brute-force) или спам-регистраций:
- Более 1000 запросов в секунду к `/login` — перебор паролей
- Более 1000 запросов в секунду к `/register` — заполнение БД мусором
- При 6 ролях и возможности регистрировать пользователей любой роли — дополнительный вектор

### Как исправил
Rate limiting **не реализован**. Рекомендуемое решение — добавление `slowapi`:

```python
# pip install slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@router.post("/login")
@limiter.limit("10/minute")  # ← 10 попыток логина в минуту
async def login(data: UserLogin, request: Request, ...):
    ...

@router.post("/register")
@limiter.limit("3/minute")   # ← 3 регистрации в минуту с одного IP
async def register(data: UserCreate, request: Request, ...):
    ...
```

---

## Проблема 7: Отсутствие эндпоинта смены пароля

### Что сгенерировал ИИ
ИИ не создал эндпоинт для смены пароля. Пользователь мог только зарегистрироваться и войти — изменить пароль было невозможно.

### В чём проблема
Если пароль скомпрометирован, пользователь не может его сменить. Единственный выход — удаление аккаунта администратором и повторная регистрация. Отсутствие базовой функции управления учётной записью.

### Как исправил
Добавлен эндпоинт `POST /api/v1/auth/change-password`:

```python
# app/auth/router.py
@router.post("/change-password", response_model=dict)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    await auth_service.change_password(db, current_user.id, data)
    return {"message": "Пароль успешно изменён."}
```

Модель и сервис:

```python
# app/auth/models.py
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

# app/auth/service.py
async def change_password(self, db, user_id, data):
    user = await self.get_by_id(db, user_id)
    if not verify_password(data.old_password, user.hashed_password):
        raise MarketPlaceError("Неверный текущий пароль.", 400)
    if data.old_password == data.new_password:
        raise MarketPlaceError("Новый пароль должен отличаться от текущего.", 400)
    user.hashed_password = hash_password(data.new_password)
    await db.flush()
```

---

## Проблема 8: JWT-токен живёт 24 часа

### Что сгенерировал ИИ
```python
# app/auth/config.py (исходная версия)
jwt_expire_minutes: int = 1440  # 24 часа
```

### В чём проблема
Токен действителен в течение 24 часов. Если токен перехвачен (XSS, небезопасное хранение в localStorage, сниффинг), злоумышленник может использовать его целые сутки. Для маркетплейса с финансовыми операциями (заказы, комиссии) это критично.

### Как исправил
Время жизни токена уменьшено до 60 минут:

```python
# app/auth/config.py (исправленная версия)
jwt_expire_minutes: int = 60  # 1 час
```

Дополнительно: при реализации refresh-токенов (опционально) время жизни access token может быть ещё меньше (15–30 минут).

---

## Проблема 9: Mass Assignment в `update_profile()`

### Что сгенерировал ИИ
```python
# app/auth/service.py (исходная версия)
async def update_profile(self, db, user_id, data):
    user = await self.get_by_id(db, user_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)  # ← любой атрибут!
```

### В чём проблема
Цикл `setattr(user, field, value)` применяет все переданные поля без белого списка (CWE-915 — массовое присвоение). Если в будущем в `UserUpdate` добавится поле `role: UserRole`, любой пользователь сможет установить себе роль `admin` через `PATCH /api/v1/auth/me`.

### Как исправил
В схеме `UserUpdate` оставлены только безопасные поля — `full_name`, `phone`, `email`:

```python
# app/auth/models.py
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
```

Поля `role`, `is_active`, `password` отсутствуют в схеме — массовое присвоение невозможно. Для дополнительной защиты рекомендуется заменить `setattr` на явное присваивание:

```python
# Рекомендуемая замена
if data.full_name is not None:
    user.full_name = data.full_name
if data.phone is not None:
    user.phone = data.phone
if data.email is not None:
    user.email = data.email
```

---

## Проблема 10: Отсутствие проверки ownership в CRUD-сервисах

### Что сгенерировал ИИ
Сервисы не проверяли, принадлежит ли изменяемый объект текущему пользователю:

```python
# app/services/product_service.py (исходная версия)
async def update(self, product_id, data):
    product = await self.get_by_id(product_id)
    # ← нет проверки: является ли текущий пользователь владельцем?
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    return product
```

### В чём проблема
Даже после добавления `Depends(get_current_user)` на роутеры, любой аутентифицированный пользователь мог изменить или удалить **чужие** товары, отзывы, заказы. Продавец A мог удалить товар продавца B.

### Как исправил
Добавлена проверка владельца через параметры `user_id` и `user_role`:

```python
# app/services/product_service.py (исправленная версия)
async def update(self, product_id, data, user_id, user_role):
    product = await self.get_by_id(product_id)

    # Проверка прав: владелец товара или модератор/админ
    if user_role not in MODERATION_ROLE_VALUES and product.seller_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения этого товара.",
        )
    # ... обновление полей
```

Аналогичные проверки добавлены в `ReviewService.update()`, `OrderService.update_status()`, `SellerService.update()`.

---

## Проблема 11: `buyer_name` не привязан к `current_user`

### Что сгенерировал ИИ
```python
# app/services/order_service.py (исходная версия)
async def create(self, data: OrderCreate) -> OrderORM:
    # ...
    order = OrderORM(
        product_id=data.product_id,
        seller_id=data.seller_id,
        buyer_name=data.buyer_name,  # ← из тела запроса!
        quantity=data.quantity,
        total_price=total_price,
    )
```

### В чём проблема
Покупатель может указать любое имя в поле `buyer_name` при создании заказа. Ничто не мешает создать заказ от имени другого пользователя. Аналогичная проблема в `ReviewService.create()` — отзыв можно оставить от чужого имени.

### Как исправил
`buyer_name` устанавливается из JWT-токена, а не из тела запроса:

```python
# app/services/order_service.py (исправленная версия)
async def create(self, data: OrderCreate, buyer_username: str) -> OrderORM:
    # ...
    order = OrderORM(
        product_id=data.product_id,
        seller_id=data.seller_id,
        buyer_name=buyer_username,  # ← из параметра, переданного роутером
        quantity=data.quantity,
        total_price=total_price,
    )

# app/routers/orders.py
@router.post("/", ...)
async def create_order(
    data: OrderCreate,
    service: OrderService = Depends(get_order_service),
    current_user: UserORM = Depends(require_buyer),
):
    return await service.create(data, buyer_username=current_user.username)
    # current_user.username — из JWT
```

---

## Проблема 12: Timing oracle на `/login`

### Что сгенерировал ИИ
```python
# app/auth/service.py (исходная версия)
async def authenticate(self, db, data):
    user = await db.execute(
        select(UserORM).where(UserORM.username == data.username)
    ).scalar_one_or_none()

    if not user:                        # ← ранний выход
        raise MarketPlaceError("Неверное имя пользователя или пароль.", 401)
    # ^ время ответа ~5 мс (только SQL-запрос)

    if not verify_password(data.password, user.hashed_password):
        raise MarketPlaceError("Неверное имя пользователя или пароль.", 401)
    # ^ время ответа ~200 мс (bcrypt — дорогой)
```

### В чём проблема
Разница во времени ответа между существующим и несуществующим пользователем (~5 мс vs ~200 мс) позволяет атакующему:
- За несколько сотен запросов определить, какие email/username зарегистрированы в системе
- Собрать базу пользователей для целевого брутфорса (CWE-208 — Timing Oracle)

### Как исправил
Добавлен фиктивный хэш — bcrypt выполняется в любом случае:

```python
# app/auth/service.py (исправленная версия)
_DUMMY_HASH = hash_password("__timing_mitigation_dummy__")

async def authenticate(self, db, data):
    user = await db.execute(
        select(UserORM).where(UserORM.username == data.username)
    ).scalar_one_or_none()

    # bcrypt выполняется ВСЕГДА — для существующего и несуществующего пользователя
    password_hash = user.hashed_password if user else _DUMMY_HASH
    password_valid = verify_password(data.password, password_hash)

    if not password_valid or user is None:
        raise MarketPlaceError("Неверное имя пользователя или пароль.", 401)
```

---

## Сводная таблица

| # | Проблема | Файл | Серьёзность | Статус |
|---|---|---|---|---|
| 1 | Мёртвый импорт `app/logger.py` | 7 файлов | 🔴 Критично | ✅ Исправлено |
| 2 | Нет аутентификации на CRUD | 5 роутеров | 🔴 Критично | ✅ Исправлено |
| 3 | JWT-секрет в коде | `auth/config.py` | 🔴 Критично | ✅ Исправлено |
| 4 | Пароль БД в коде | `config.py` | 🔴 Критично | ✅ Исправлено |
| 5 | CORS `allow_origins=["*"]` | `main.py` | 🟠 Высокая | ✅ Исправлено |
| 6 | Нет rate limiting | `/login`, `/register` | 🟠 Высокая | ⬜ Не исправлено* |
| 7 | Нет смены пароля | отсутствовал | 🟠 Высокая | ✅ Исправлено |
| 8 | JWT живёт 24 часа | `auth/config.py` | 🟠 Высокая | ✅ Исправлено |
| 9 | Mass Assignment | `auth/service.py` | 🟡 Средняя | ✅ Исправлено |
| 10 | Нет ownership check | CRUD-сервисы | 🟠 Высокая | ✅ Исправлено |
| 11 | `buyer_name` из тела запроса | `order_service.py` | 🟠 Высокая | ✅ Исправлено |
| 12 | Timing oracle на `/login` | `auth/service.py` | 🟡 Средняя | ✅ Исправлено |

*\* Rate limiting не реализован — рекомендовано добавление `slowapi` (см. проблему 6)*
