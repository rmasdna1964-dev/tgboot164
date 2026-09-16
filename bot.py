import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"
MY_TELEGRAM_ID = 8706958823

dp = Dispatcher()
games = {}


@dp.message(F.text.in_({".paystart", "/paystart", "🎮 Играть в Камень, ножницы, бумага"}))
async def paystart_handler(message: types.Message, bot: Bot):
  user = message.from_user
  user_id = user.id
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"
  chat_id = message.chat.id

  # Создаем игровую сессию
  games[user_id] = {
      "status": "waiting_admin",
      "host_id": user_id,
      "host_name": user_name,
      "guest_id": None,
      "guest_name": None,
      "chat_id": chat_id,
      "host_choice": None,
      "guest_choice": None,
  }

  await message.answer(
      f"⏳ <b>{user_name}</b>, запрос на игру принят секретарем!\n\n"
      "Ожидаем подтверждения от администратора..."
  )

  notification_text = (
      "🎮 <b>Новый запрос на игру (.paystart)!</b>\n\n"
      f"👤 Игрок: {user_name} ({user_username})\n"
      f"🆔 ID: {user_id}\n\n"
      "Нажми кнопку ниже, чтобы открыть комнату:"
  )

  admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="✅ Разрешить игру", callback_data=f"room_ok_{user_id}"
      )
  ]])

  try:
    await bot.send_message(
        chat_id=MY_TELEGRAM_ID,
        text=notification_text,
        reply_markup=admin_keyboard,
    )
  except Exception as e:
    logging.error(f"Ошибка отправки уведомления админу: {e}")


@dp.callback_query(F.data.startswith("room_ok_"))
async def admin_confirm_room(callback: types.CallbackQuery, bot: Bot):
  host_id = int(callback.data.split("_")[2])

  if host_id in games:
    games[host_id]["status"] = "waiting_guest"
    target_chat_id = games[host_id]["chat_id"]

    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ СТАТУС: Игра подтверждена админом!"
    )
    await callback.answer("Комната успешно открыта!")

    join_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Войти в игру (Второй игрок)",
            callback_data=f"join_{host_id}",
        )
    ]])

    try:
      await bot.send_message(
          chat_id=target_chat_id,
          text=(
              f"🟢 Секретарь подтвердил игру, которую создал(а) <b>"
              f"{games[host_id]['host_name']}</b>!\n\n"
              "Кто хочет сыграть? Нажмите кнопку ниже, чтобы занять второй слот:"
          ),
          reply_markup=join_keyboard,
      )
    except Exception as e:
      logging.error(f"Ошибка отправки в чат: {e}")
  else:
    await callback.answer("Эта сессия уже неактивна.", show_alert=True)


@dp.callback_query(F.data.startswith("join_"))
async def join_game(callback: types.CallbackQuery, bot: Bot):
  host_id = int(callback.data.split("_")[1])
  guest = callback.from_user

  if host_id not in games or games[host_id]["status"] != "waiting_guest":
    await callback.answer("Эта игра уже началась или закрыта!", show_alert=True)
    return

  if guest.id == host_id:
    await callback.answer("Нельзя играть против самого себя!", show_alert=True)
    return

  games[host_id]["guest_id"] = guest.id
  games[host_id]["guest_name"] = guest.full_name
  games[host_id]["status"] = "playing"

  choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [
          InlineKeyboardButton(
              text="🪨 Камень", callback_data=f"move_{host_id}_stone"
          ),
          InlineKeyboardButton(
              text="✂️ Ножницы", callback_data=f"move_{host_id}_scissors"
          ),
      ],
      [
          InlineKeyboardButton(
              text="📄 Бумага", callback_data=f"move_{host_id}_paper"
          )
      ],
  ])

  await callback.message.edit_text(
      f"⚔️ Дуэль (Камень, ножницы, бумага) началась!\n\n"
      f"👤 Игрок 1: <b>{games[host_id]['host_name']}</b>\n"
      f"👤 Игрок 2: <b>{guest.full_name}</b>\n\n"
      "👇 <b>Оба участника, сделайте свой выбор ниже:</b>",
      reply_markup=choice_keyboard,
  )
  await callback.answer("Вы успешно вошли в игру!")


@dp.callback_query(F.data.startswith("move_"))
async def process_move(callback: types.CallbackQuery, bot: Bot):
  parts = callback.data.split("_")
  host_id = int(parts[1])
  move = parts[2]

  if host_id not in games or games[host_id]["status"] != "playing":
    await callback.answer("Игра неактивна или уже завершена!", show_alert=True)
    return

  game = games[host_id]
  user_id = callback.from_user.id

  if user_id != game["host_id"] and user_id != game["guest_id"]:
    await callback.answer("Вы не участник этой дуэли!", show_alert=True)
    return

  choices_rus = {
      "stone": "🪨 Камень",
      "scissors": "✂️ Ножницы",
      "paper": "📄 Бумага",
  }

  # Фиксируем ход игрока
  if user_id == game["host_id"]:
    if game["host_choice"] is not None:
      await callback.answer("Вы уже сделали свой выбор!", show_alert=True)
      return
    game["host_choice"] = move
  else:
    if game["guest_choice"] is not None:
      await callback.answer("Вы уже сделали свой выбор!", show_alert=True)
      return
    game["guest_choice"] = move

  await callback.answer(f"Ваш выбор принят: {choices_rus[move]}")

  # Если оба сходили — подводим итоги
  if game["host_choice"] and game["guest_choice"]:
    h_choice = game["host_choice"]
    g_choice = game["guest_choice"]

    if h_choice == g_choice:
      res_text = "🤝 Ничья!"
    elif (
        (h_choice == "stone" and g_choice == "scissors")
        or (h_choice == "scissors" and g_choice == "paper")
        or (h_choice == "paper" and g_choice == "stone")
    ):
      res_text = f"🎉 Победил(а) {game['host_name']}!"
    else:
      res_text = f"🎉 Победил(а) {game['guest_name']}!"

    final_msg = (
        "🏁 <b>Результаты дуэли!</b>\n\n"
        f"👤 {game['host_name']}: {choices_rus[h_choice]}\n"
        f"👤 {game['guest_name']}: {choices_rus[g_choice]}\n\n"
        f"<b>{res_text}</b>"
    )

    try:
      await callback.message.edit_text(final_msg)
    except Exception:
      pass

    # Отчет администратору
    report = (
        "📊 Секретарь: Дуэль завершена!\n\n"
        f"Игроки: {game['host_name']} vs {game['guest_name']}\n"
        f"Ходы: {choices_rus[h_choice]} / {choices_rus[g_choice]}\n"
        f"Итог: {res_text}"
    )
    try:
      await bot.send_message(chat_id=MY_TELEGRAM_ID, text=report)
    except Exception:
      pass

    games.pop(host_id, None)
  else:
    try:
      await callback.message.edit_text(
          f"✅ Ваш выбор ({choices_rus[move]}) записан.\n⏳ Ожидаем ход"
          " соперника..."
      )
    except Exception:
      pass


async def main() -> None:
  bot = Bot(
      token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
  )
  await bot.delete_webhook(drop_pending_updates=True)
  logging.info("Бот-секретарь успешно запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())
