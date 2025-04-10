from nicegui import ui
from collections import deque
import asyncio
from sqlalchemy.orm import Session
import crud
from models import User, Equipment, Rental
from database import SessionLocal

db = SessionLocal()

async def get_nfc_input(prompt_message: str) -> str:
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

async def nfc_equipment_rental_workflow(update_callback=None):
    """
    Процесс создания новой аренды или возврата оборудования с использованием NFC:
    1. Сканирование оборудования
    2. Проверка статуса аренды оборудования
    3. Если арендовано - возврат, если нет - продолжение процесса аренды:
       3.1. Сканирование пропуска пользователя
       3.2. Подтверждение аренды и создание записи
       
    Args:
        update_callback: Функция обратного вызова для обновления списков оборудования
    """
    if db is None:
        ui.notify("Ошибка подключения к базе данных", color="negative")
        return
    
    # Получение NFC оборудования
    equipment_nfc = await get_nfc_input("Scan device")
    if not equipment_nfc:
        ui.notify("Сканирование устройства отменено", color="warning")
        return
    
    # Поиск оборудования по NFC
    equipment = crud.find_equipment_by_nfc(db, equipment_nfc)
    if not equipment:
        ui.notify(f"Оборудование с NFC {equipment_nfc} не найдено", color="negative")
        return
    
    # Проверка, не находится ли оборудование уже в аренде
    rental = crud.is_equipment_rented(db, equipment.id_eq)
    
    if rental:
        # Оборудование уже арендовано, показываем диалог возврата
        dialog = ui.dialog()
        confirmed = asyncio.Future()
        
        def on_confirm():
            crud.return_equipment(db, rental.id_re)
            ui.notify('Оборудование успешно возвращено', color="positive")
            dialog.close()
            confirmed.set_result(True)
            # Обновляем списки оборудования после возврата
            if update_callback:
                update_callback()
        
        def on_cancel():
            dialog.close()
            confirmed.set_result(False)
        
        with dialog, ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(text='Возврат оборудования').style('font-size: 200%')
                ui.button(icon='close', on_click=on_cancel).props('flat round')
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(f"{equipment.name}").style('font-weight: bold; font-size: 16px')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Unknown'}")
            ui.html(f"Арендовано: <b>{rental.user.name}</b>")
            ui.label(f"Отдел: {rental.user.department.name}")
            ui.label(f"Арендовано с: {rental.rental_start.strftime('%Y-%m-%d %H:%M')}")
            
            if rental.comment:
                ui.label("Комментарий:").style('margin-top: 10px; font-weight: bold')
                ui.label(rental.comment).style('white-space: pre-wrap')
            
            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=on_cancel).props('outline')
                ui.button('Подтвердить возврат', on_click=on_confirm).props('unelevated color=primary')
        
        dialog.open()
        await confirmed
        
    else:
        # Оборудование не арендовано, продолжаем процесс аренды
        # Получение NFC пользователя
        user_nfc = await get_nfc_input("Scan your pass")
        user_nfc = user_nfc.lower()
        if not user_nfc:
            ui.notify("Сканирование пропуска отменено", color="warning")
            return
        
        # Поиск пользователя по NFC
        user = crud.find_user_by_nfc(db, user_nfc)
        if not user:
            ui.notify(f"Пользователь с NFC {user_nfc} не найден", color="negative")
            return
        
        # Показать диалог подтверждения
        dialog = ui.dialog()
        confirmed = asyncio.Future()
        
        comment_text = ""
        
        def on_confirm():
            dialog.close()
            confirmed.set_result(True)
        
        def on_cancel():
            dialog.close()
            confirmed.set_result(False)
        
        def on_comment_change(e):
            nonlocal comment_text
            comment_text = e.value
        
        with dialog, ui.card():
            ui.label('Подтверждение аренды').classes('text-h5')
            
            with ui.separator():
                pass
            
            with ui.row():
                with ui.column():
                    ui.label('Пользователь:').classes('text-subtitle1')
                    ui.label(f"{user.name}").classes('text-body1')
                    ui.label(f"Отдел: {user.department.name}").classes('text-body1')
                
                with ui.column():
                    ui.label('Оборудование:').classes('text-subtitle1')
                    ui.label(f"{equipment.name}").classes('text-body1')
                    ui.label(f"Тип: {equipment.etype.name if equipment.etype else 'Не указан'}").classes('text-body1')
                    ui.label(f"Серийный номер: {equipment.serialnum or 'Не указан'}").classes('text-body1')
            
            with ui.separator():
                pass
                
            ui.input('Комментарий (опционально)', on_change=on_comment_change)
            
            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=on_cancel).props('outline')
                ui.button('Подтвердить', on_click=on_confirm).props('unelevated color=primary')
        
        dialog.open()
        
        # Ожидаем результат подтверждения
        result = await confirmed
        
        if result:
            try:
                # Создаем запись аренды
                rental = crud.create_rental(db, user.id_us, equipment.id_eq, comment_text)
                ui.notify("Аренда успешно создана", color="positive")
                # Обновляем списки оборудования после аренды
                if update_callback:
                    update_callback()
            except Exception as e:
                ui.notify(f"Ошибка при создании аренды: {str(e)}", color="negative")
        else:
            ui.notify("Операция отменена", color="warning")

# Пример использования в приложении NiceGUI
def main():
    ui.button('Сканировать и арендовать', on_click=nfc_equipment_rental_workflow)
    ui.run()

if __name__ in {'__main__', '__mp_main__'}:
    main()