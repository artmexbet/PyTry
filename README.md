# PyTry
## Быстрый старт
Для корректной работы создайте файл _config.py_

В него необходимо поместить следующие поля
* _db_password_ - пароль от базы данных
* _db_username_ = "postgres"
* _db_address_ = "localhost"  # путь до базы данных
* _db_name_ = "PyTryDB"  # имя базы данных

Так же нужно создать базу данных у пользователя 
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

### /courses/<course_id>/<lesson_id>
**GET**

**JWT REQUIRED**

**response:**

* status - не факт, что придёт :) ["User not at course", "Not found"]
* id
* name
* description
* task - [task_info]
* links - [link_info]

### /courses/<course_id>/<lesson_id>/<task_id>
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
