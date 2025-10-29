# Requirements Document

## Introduction

Данная функциональность добавляет возможность генерации Data Matrix кодов для пользователей и оборудования в системе аренды. Коды будут содержать NFC идентификаторы из базы данных и сохраняться как PNG изображения с текстовыми подписями.

## Glossary

- **NfcScan_System**: Модуль NfcScan.py, отвечающий за работу с NFC сканированием и связанными функциями
- **Main_System**: Главный модуль main.py, содержащий Admin Panel и основной интерфейс приложения
- **User_Entity**: Сущность пользователя из таблицы users с полями id_us, name, nfc
- **Equipment_Entity**: Сущность оборудования из таблицы equipment с полями id_eq, name, serialnum, nfc
- **DataMatrix_Code**: Двумерный штрих-код в формате Data Matrix
- **PNG_File**: Файл изображения в формате PNG
- **Database_Session**: Сессия подключения к базе данных SQLite
- **Admin_Panel**: Административная панель в главном окне приложения
- **Dialog_Window**: Диалоговое окно для выбора опций генерации кодов
- **Batch_Generation**: Процесс массовой генерации кодов для множества объектов

## Requirements

### Requirement 1

**User Story:** Как администратор системы, я хочу генерировать Data Matrix коды для пользователей, чтобы создавать физические карты доступа с кодами.

#### Acceptance Criteria

1. WHEN администратор вызывает функцию генерации кода пользователя, THE NfcScan_System SHALL считать поле nfc из таблицы users для указанного пользователя
2. WHEN поле nfc получено из базы данных, THE NfcScan_System SHALL создать DataMatrix_Code содержащий значение nfc
3. WHEN DataMatrix_Code создан, THE NfcScan_System SHALL добавить текстовую подпись с именем пользователя под кодом
4. WHEN изображение с кодом и текстом сформировано, THE NfcScan_System SHALL сохранить его как PNG_File
5. IF поле nfc пустое или отсутствует, THEN THE NfcScan_System SHALL вернуть ошибку с соответствующим сообщением

### Requirement 2

**User Story:** Как администратор системы, я хочу генерировать Data Matrix коды для оборудования, чтобы создавать физические метки для инвентаря.

#### Acceptance Criteria

1. WHEN администратор вызывает функцию генерации кода оборудования, THE NfcScan_System SHALL считать поле nfc из таблицы equipment для указанного оборудования
2. WHEN поле nfc получено из базы данных, THE NfcScan_System SHALL создать DataMatrix_Code содержащий значение nfc
3. WHEN DataMatrix_Code создан, THE NfcScan_System SHALL добавить текстовую подпись с именем оборудования и серийным номером под кодом
4. WHEN изображение с кодом и текстом сформировано, THE NfcScan_System SHALL сохранить его как PNG_File
5. IF поле nfc пустое или отсутствует, THEN THE NfcScan_System SHALL вернуть ошибку с соответствующим сообщением

### Requirement 3

**User Story:** Как разработчик, я хочу иметь отдельные функции для генерации кодов пользователей и оборудования, чтобы легко интегрировать их в различные части системы.

#### Acceptance Criteria

1. THE NfcScan_System SHALL содержать функцию generate_user_datamatrix принимающую user_id как параметр
2. THE NfcScan_System SHALL содержать функцию generate_equipment_datamatrix принимающую equipment_id как параметр
3. WHEN любая из функций вызывается, THE NfcScan_System SHALL использовать Database_Session для получения данных
4. WHEN генерация завершена успешно, THE NfcScan_System SHALL вернуть путь к созданному PNG_File
5. IF произошла ошибка во время генерации, THEN THE NfcScan_System SHALL вернуть None и вывести сообщение об ошибке

### Requirement 4

**User Story:** Как администратор системы, я хочу иметь кнопку в Admin Panel для доступа к функциям генерации кодов, чтобы легко управлять созданием Data Matrix кодов через графический интерфейс.

#### Acceptance Criteria

1. THE Main_System SHALL содержать кнопку "Генерация кодов" в Admin Panel
2. WHEN администратор нажимает кнопку генерации кодов, THE Main_System SHALL открыть диалоговое окно с опциями генерации
3. THE Dialog_Window SHALL содержать две основные кнопки для массовой генерации
4. THE Dialog_Window SHALL позволить пользователю выбрать папку для сохранения файлов
5. WHEN диалоговое окно открыто, THE Main_System SHALL отображать понятный интерфейс с описанием функций

### Requirement 5

**User Story:** Как администратор системы, я хочу генерировать Data Matrix коды для всех пользователей одновременно, чтобы создать полный набор карт доступа за один раз.

#### Acceptance Criteria

1. THE Dialog_Window SHALL содержать кнопку "Генерировать коды для всех пользователей"
2. WHEN администратор нажимает кнопку генерации для пользователей, THE Main_System SHALL запросить выбор папки для сохранения
3. WHEN папка выбрана, THE Main_System SHALL получить список всех пользователей из базы данных
4. THE Main_System SHALL генерировать Data Matrix код для каждого пользователя с непустым nfc полем
5. WHEN код сгенерирован, THE Main_System SHALL сохранить изображение как PNG_File с именем "user_[id]_[name].png"
6. THE Main_System SHALL отображать прогресс генерации и количество созданных файлов
7. IF у пользователя отсутствует nfc поле, THEN THE Main_System SHALL пропустить этого пользователя и записать в лог

### Requirement 6

**User Story:** Как администратор системы, я хочу генерировать Data Matrix коды для всего оборудования одновременно, чтобы создать полный набор меток для инвентаря за один раз.

#### Acceptance Criteria

1. THE Dialog_Window SHALL содержать кнопку "Генерировать коды для всего оборудования"
2. WHEN администратор нажимает кнопку генерации для оборудования, THE Main_System SHALL запросить выбор папки для сохранения
3. WHEN папка выбрана, THE Main_System SHALL получить список всего оборудования из базы данных
4. THE Main_System SHALL генерировать Data Matrix код для каждого оборудования с непустым nfc полем
5. WHEN код сгенерирован, THE Main_System SHALL сохранить изображение как PNG_File с именем "equipment_[id]_[name].png"
6. THE Main_System SHALL отображать прогресс генерации и количество созданных файлов
7. IF у оборудования отсутствует nfc поле, THEN THE Main_System SHALL пропустить это оборудование и записать в лог