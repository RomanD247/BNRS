# Requirements Document

## Introduction

Интеграция функций обновления NFC кодов из файла fill_nfc_fields.py в основной код приложения. Система должна предоставить пользователям возможность обновлять NFC коды для пользователей и оборудования через кнопки в главном интерфейсе.

## Glossary

- **MatrixCode Module**: Новый модуль, содержащий функции для обновления NFC кодов
- **NFC Code**: Уникальный код, генерируемый на основе данных пользователя или оборудования
- **User NFC Format**: Формат NFC кода для пользователей: id_us_name_id_dep (в нижнем регистре)
- **Equipment NFC Format**: Формат NFC кода для оборудования: id_eq_name_serialnum (в нижнем регистре)
- **Main Interface**: Главный интерфейс приложения в файле main.py
- **Database Session**: Сессия подключения к базе данных SQLAlchemy

## Requirements

### Requirement 1

**User Story:** Как администратор системы, я хочу обновить NFC коды всех пользователей одним нажатием кнопки, чтобы синхронизировать коды с текущими данными пользователей.

#### Acceptance Criteria

1. WHEN администратор нажимает кнопку "Update Users Codes", THE MatrixCode Module SHALL обновить NFC поля для всех пользователей в таблице users
2. THE MatrixCode Module SHALL генерировать NFC код в формате id_us_name_id_dep в нижнем регистре
3. THE MatrixCode Module SHALL пропускать пользователей с отсутствующими обязательными данными (name или id_dep)
4. THE MatrixCode Module SHALL перезаписывать существующие NFC коды новыми значениями
5. THE MatrixCode Module SHALL возвращать количество обновленных записей пользователей

### Requirement 2

**User Story:** Как администратор системы, я хочу обновить NFC коды всего оборудования одним нажатием кнопки, чтобы синхронизировать коды с текущими данными оборудования.

#### Acceptance Criteria

1. WHEN администратор нажимает кнопку "Update Equipments Codes", THE MatrixCode Module SHALL обновить NFC поля для всего оборудования в таблице equipment
2. THE MatrixCode Module SHALL генерировать NFC код в формате id_eq_name_serialnum в нижнем регистре
3. THE MatrixCode Module SHALL пропускать оборудование с отсутствующими обязательными данными (name или serialnum)
4. THE MatrixCode Module SHALL перезаписывать существующие NFC коды новыми значениями
5. THE MatrixCode Module SHALL возвращать количество обновленных записей оборудования

### Requirement 3

**User Story:** Как администратор системы, я хочу видеть результат операции обновления NFC кодов, чтобы знать, сколько записей было обновлено и были ли ошибки.

#### Acceptance Criteria

1. THE MatrixCode Module SHALL обрабатывать исключения базы данных и возвращать информацию об ошибках
2. THE MatrixCode Module SHALL выполнять откат транзакции при возникновении ошибок
3. THE MatrixCode Module SHALL закрывать сессию базы данных после завершения операции
4. THE MatrixCode Module SHALL возвращать статус операции (успех/ошибка) и количество обновленных записей
5. THE Main Interface SHALL отображать результат операции пользователю через status_label

### Requirement 4

**User Story:** Как разработчик, я хочу иметь отдельный модуль MatrixCode.py для функций обновления NFC кодов, чтобы код был организован и переиспользуем.

#### Acceptance Criteria

1. THE MatrixCode Module SHALL быть создан как отдельный файл MatrixCode.py
2. THE MatrixCode Module SHALL содержать функцию update_user_codes для обновления NFC кодов пользователей
3. THE MatrixCode Module SHALL содержать функцию update_equipment_codes для обновления NFC кодов оборудования
4. THE MatrixCode Module SHALL использовать существующие модели User и Equipment из models.py
5. THE Main Interface SHALL импортировать и использовать функции из MatrixCode Module

### Requirement 5

**User Story:** Как администратор системы, я хочу, чтобы кнопки в главном интерфейсе были правильно подключены к новым функциям, чтобы операции обновления выполнялись корректно.

#### Acceptance Criteria

1. THE Main Interface SHALL заменить неправильные имена функций в строках 421 и 427 на корректные имена функций
2. THE Main Interface SHALL подключить кнопку "Update Users Codes" к функции update_user_codes
3. THE Main Interface SHALL подключить кнопку "Update Equipments Codes" к функции update_equipment_codes
4. THE Main Interface SHALL передавать необходимые параметры функциям обновления
5. THE Main Interface SHALL обрабатывать возвращаемые значения функций и отображать результат