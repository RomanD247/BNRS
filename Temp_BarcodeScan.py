from nicegui import ui

def main():
    all_keys = []                         # Полный буфер для введённых символов
    termination_sequence = ";'"           # Завершающая последовательность

    # Создаем диалоговое окно
    dialog = ui.dialog()

    with dialog.props('persistent') as dialog, ui.card():
        ui.label('Введите последовательность с клавиатуры...')
        result_label = ui.label()
        # Кнопка для закрытия диалога
        ui.button('Закрыть диалог', on_click=lambda: close_dialog())

    # Обработчик клавиш
    def on_key(e):
        # Обрабатываем только события отпускания клавиши (keyup)
        if not e.action.keyup:
            return

        key_str = str(e.key)
        if len(key_str) != 1 or not key_str.isprintable():
            return

        # Добавляем символ в общий буфер
        all_keys.append(key_str)
        print("Набрано: ", "".join(all_keys))
        
        # Если длина буфера меньше длины завершающей последовательности, то продолжаем сбор
        if len(all_keys) < len(termination_sequence):
            return
        
        # Проверяем, соответствуют ли последние символы завершающей последовательности
        if "".join(all_keys[-len(termination_sequence):]) == termination_sequence:
            # Формируем результат, исключая завершающую последовательность
            result = "".join(all_keys[:-len(termination_sequence)])
            result_label.text = f'🎉 Вы набрали: {result}'
            # Отключаем дальнейшую обработку клавиш (можно также очистить буфер, если требуется)
            keyboard.active = False

    # Регистрируем глобальный обработчик клавиатуры и выключаем его до открытия диалога
    keyboard = ui.keyboard(on_key)
    keyboard.active = False

    # Функция для открытия диалога с активацией трекинга клавиш
    def open_dialog():
        all_keys.clear()         # Сброс буфера при открытии диалога
        keyboard.active = True   # Активируем обработку клавиш
        dialog.open()

    # Функция для закрытия диалога с деактивацией трекинга клавиш
    def close_dialog():
        keyboard.active = False  # Отключаем обработку клавиш
        dialog.close()

    # Кнопка для открытия диалога
    ui.button('Открыть диалог', on_click=open_dialog)

if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run()
