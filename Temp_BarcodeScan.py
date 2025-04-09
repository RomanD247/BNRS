from nicegui import ui
from collections import deque

def main():
    max_buffer_length = 100       # Максимальная длина буфера

    # Создаем диалоговое окно
    dialog = ui.dialog()

    with dialog.props('persistent') as dialog, ui.card():
        ui.label('Введите текст с клавиатуры и нажмите Enter...')
        result_label = ui.label()
        # Кнопка для закрытия диалога
        ui.button('Закрыть диалог', on_click=lambda: close_dialog())

    all_keys = deque(maxlen=max_buffer_length)

    def process_input(entered_sequence):
        result_label.text = f'🎉 Вы набрали: {entered_sequence}'
        print(f"Введенный текст: {entered_sequence}")
        close_dialog()

    def on_key(e):
        # Обрабатываем только события отпускания клавиши (keyup)
        if not e.action.keyup:
            return

        key_str = str(e.key)

        # Проверяем, является ли нажатая клавиша Enter
        if e.key == 'Enter':
            entered_text = "".join(list(all_keys))
            process_input(entered_text)
            keyboard.active = False  # Отключаем обработку после Enter
            return

        # Добавляем только печатные символы в буфер
        if len(key_str) == 1 and key_str.isprintable():
            all_keys.append(key_str)
            print("Набрано: ", "".join(all_keys))

    # Регистрируем глобальный обработчик клавиатуры и выключаем его до открытия диалога
    keyboard = ui.keyboard(on_key)
    keyboard.active = False

    # Функция для открытия диалога с активацией трекинга клавиш
    def open_dialog():
        all_keys.clear()  # Сброс буфера при открытии диалога
        result_label.text = '' # Очищаем предыдущее сообщение
        keyboard.active = True  # Активируем обработку клавиш
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


    '''Ниже дополненный пример кода
    Он обёрнут в функцию и вызывается командой в примере main()'''

from nicegui import ui
from collections import deque
import asyncio

async def get_user_input(prompt_message: str) -> str:
    """
    Открывает диалоговое окно с запросом и возвращает введенный пользователем текст после нажатия Enter.

    Args:
        prompt_message: Сообщение, отображаемое в диалоговом окне.

    Returns:
        Введенный пользователем текст (строка).
    """
    result = ""
    all_keys = deque()
    dialog = ui.dialog()
    closed = asyncio.Future()

    def on_key(e):
        nonlocal result
        if not e.action.keyup:
            return

        key_str = str(e.key)

        if e.key == 'Enter':
            result = "".join(list(all_keys))
            keyboard.active = False
            dialog.close()
            closed.set_result(None)  # Разблокируем ожидание
            return

        if len(key_str) == 1 and key_str.isprintable():
            all_keys.append(key_str)
            print("Набрано: ", "".join(all_keys))

    def close_dialog():
        keyboard.active = False
        dialog.close()
        closed.set_result(None) # Разблокируем ожидание даже при закрытии без Enter

    with dialog, ui.card():
        ui.label(prompt_message)
        input_display = ui.label()

        def update_display():
            input_display.text = "".join(list(all_keys))

        #ui.timer(0.1, update_display, active=True) # Обновляем отображение ввода

        ui.button('Закрыть', on_click=close_dialog)

        keyboard = ui.keyboard(on_key)
        keyboard.active = True

    dialog.open()
    await closed  # Ожидаем, пока диалог не будет закрыт (через Enter или кнопку)
    return result

def main():
    async def handle_input():
        message = "Please scan you personal pass card!"
        name = await get_user_input(message)
        ui.notify(f"Вы ввели: {name}")

        message = "Please, scan device's tag you want to rent!"
        color = await get_user_input(message)
        ui.notify(f"Ваш любимый цвет: {color}")

    ui.button("SCAN", on_click=handle_input)

if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run()