# PyTry
## Быстрый старт
### Без докера
Для корректной работы создайте файл _config.py_

В него необходимо поместить следующие поля
* _db_password_ - пароль от базы данных
* _db_username_ = "postgres"
* _db_address_ = "localhost"  # путь до базы данных
* _db_name_ = "PyTryDB"  # имя базы данных

Так же нужно создать базу данных у пользователя 
### С докером
Для работы с докером необходимо выполнить в консоли следующие команды

```
docker build .
docker-compose up -d
```
После этого сервер будет поднят на localhost:5000

Чтобы зарегистрировать нового админа в обход всех ссылок, нужно запустить файл add_user через консоль внутри докера
Это можно сделать в Docker Desktop.

## Полномочия
Пользователям были добавлены роли, из-за чего возникла потребность добавить разные полномочия разным людям.
Каждое следующее полномочие "наследует" права предыдущего внутри каждого блока
_Важно!: при создании новых ролей делать самые слабые роли маленькими буквами, а сильные - большими_
### Работа с курсами
* **/c** - просмотр любых курсов
* **/C** - возможность создавать и редактировать курсы
* **/Ca** - полный контроль над курсами
### Работа с пользователями
* **/u** - возможность смотреть пользователей на курсе
* **/U** - возможность менять роли и пароли пользователям
* **/Ua** - полный доступ

## Пути
### /reg
**POST**

**body:**

* login: str
* password: str
* name: str
* email: str

**response:**

* status - ["success", "already", "Not all arguments"]
* jwt_access
* jwt_refresh
* user (информация о пользователе в json)

### /login
**POST**

**body:**

* login: str
* password: str
* email: str (Либо логин, либо email)

**response:**

* status - ["success", "already", "Not all arguments"]
* jwt_access
* jwt_refresh
* user (информация о пользователе в json)

### /courses
**GET**

**JWT REQUIRED**

**response:**

* courses - [course_info] - список из JSON

### /courses/attend/<course_id>
**GET**

**JWT REQUIRED**

**response:**

* status - ["Forbidden", "No access", "Already on course", "success"]

### /courses/<course_id>
**GET**

**JWT REQUIRED**

**response:**

* status - не факт, что придёт :) ["Course not found", "User not at course"]
* id
* name
* description
* pic (путь до картинки)
* language - language_info
* is_public - bool
* lessons - [lesson_info]

### /lessons/<lesson_id>
**GET**

**JWT REQUIRED**

**response:**

* status - не факт, что придёт :) ["User not at course", "Not found"]
* id
* name
* description
* task - [task_info]
* links - [link_info]

### /tasks/<task_id>
**GET**

**JWT REQUIRED**

**response:**

* status - не факт, что придёт :) ["User not at course", "Not found"]
* name
* task_condition (условие)
* time_limit - максимальное время выполнения
* tests - список тестов (2 первых теста для примера)

**POST**

**JWT REQUIRED**

**body:**

* code: str

**response:**

Эта штука ужасно туманно работает (я стараюсь).
Ответ приходит потоком (как когда файлы отправляют). 
Это связано с тем, что проверяется код в отдельном потоке,
чтобы сервер не ждал завершения выполнения кода от челика.

В ответ придёт json:
* verdict - Если OK, все тесты пройдены, иначе - будет отправлено, что именно не так
* time - Время выполнения кода

Ещё в этой штуке может прийти status, но если он пришел,
то у чела, вероятно, нет доступа к курсу, или курса не существует)

### /user/courses/<user_id>

**GET**

**JWT REQUIRED**

**response:**

* courses - [course_info]
* status - тут снова всё по классике

### /refresh

**GET**

**FRESH JWT REQUIRED**

**response:**

* jwt_access

### /users/<user_id>/password

**UPDATE**

**JWT REQUIRED**

**body:**

* new_password - обязательное поле
* old_password - необязательно для админа, если он меняет чужой пароль

**response:**

* status

### /courses/<course_id>

**DELETE**

**ADMIN JWT REQUIRED**

**response:**

* status

### /lessons/<lesson_id>

**DELETE**

**ADMIN JWT REQUIRED**

**response:**

* status

### /tasks/<task_id>

**DELETE**

**ADMIN JWT REQUIRED**

**response:**

* status


### /links/<link_id>

**DELETE**

**ADMIN JWT REQUIRED**

**response:**

* status

### /users/<user_id>

**DELETE**

**ADMIN JWT REQUIRED**

Пользователя может удалять только админ.

**response:**

* status

### /languages/<language_id>

**DELETE**

**ADMIN JWT REQUIRED**

Язык может удалять только админ.

**response:**

* status

### /languages

**POST**

**ADMIN JWT REQUIRED**

**body**

* name: str
* path: str
* options: str

**response**

* status
* language - если _status = success_

### /courses

**POST**

**ADMIN JWT REQUIRED**

**body**

* name: str
* description: str
* pic: str
* language_id: str
* is_public: bool

**response**

* status
* course - если _status = success_

### /lessons

**POST**

**ADMIN JWT REQUIRED**

**body**

* name: str
* description: str
* course_id: str
* links: list[dict] ([{"title": "some title", "link": "some_link"}]) (optional)

**response**

* status
* lesson - если _status = success_

### /auth

**GET**

**JWT REQUIRED**

**response**

* info: dict - словарь с инфой о пользователе 
