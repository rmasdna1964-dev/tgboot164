import asyncio
import logging
import random
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Токен твоего бота
BOT_TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"

# Твой Telegram ID администратора
MY_TELEGRAM_ID = 8706958823

dp = Dispatcher()
game_sessions = {}


@dp.message(F.text.in_({".paystart", "/paystart"}))
async def paystart_handler(message: types.Message, bot: Bot):
  user = message.from_user
  user_id = user.id
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"
  chat_id = message.chat.id

  game_sessions[user_id] = {"status": "waiting_admin", "chat_id": chat_id}

  # Убрали опасный Markdown, чтобы избежать ошибок с символами в именах
  await message.answer(
      f"⏳ {user_name}, запрос на игру принят!\n\n"
      "Ожидаем подтверждения от администратора..."
  )

  chat_type_name = (
      "Личные сообщения"
      if message.chat.type == "private"
      else f"Группа: {message.chat.title}"
  )

  notification_text = (
      "🎮 Новый запрос на игру (.paystart)!\n\n"
      f"👤 Игрок: {user_name} ({user_username})\n"
      f"🆔 ID игрока: {user_id}\n"
      f"💬 Место запуска: {chat_type_name}\n\n"
      "Нажми кнопку ниже, чтобы разрешить игроку начать:"
  )

  admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="✅ Подтвердить старт игры", callback_data=f"start_game_{user_id}"
      )
  ]])

  try:
    await bot.send_message(
        chat_id=MY_TELEGRAM_ID,
        text=notification_text,
        reply_markup=admin_keyboard,
    )
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление админу: {e}")


@dp.callback_query(F.data.startswith("start_game_"))
async def admin_confirm_game(callback: types.CallbackQuery, bot: Bot):
  user_id = int(callback.data.split("_")[2])

  if user_id in game_sessions:
    game_sessions[user_id]["status"] = "playing"
    target_chat_id = game_sessions[user_id]["chat_id"]

    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ СТАТУС: Игра успешно разблокирована!"
    )
    await callback.answer("Игра подтверждена!")

    game_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪨 Камень", callback_data="choice_stone"),
            InlineKeyboardButton(text="✂️ Ножницы", callback_data="choice_scissors"),
        ],
        [InlineKeyboardButton(text="📄 Бумага", callback_data="choice_paper")],
    ])

    try:
      await bot.send_message(
          chat_id=target_chat_id,
          text=(
              "🟢 Администратор подтвердил старт!\n\n"
              "Игра началась! Выбери свой вариант:"
          ),
          reply_markup=game_keyboard,
      )
    except Exception as e:
      logging.error(f"Не удалось отправить сообщение в чат: {e}")
  else:
    await callback.answer("Сессия игрока не найдена.", show_alert=True)


@dp.callback_query(F.data.startswith("choice_"))
async def process_game_choice(callback: types.CallbackQuery, bot: Bot):
  user_id = callback.from_user.id

  if (
      user_id not in game_sessions
      or game_sessions[user_id]["status"] != "playing"
  ):
    await callback.answer("Эта игра неактивна или не ваша!", show_alert=True)
    return

  user_choice = callback.data.split("_")[1]
  choices_rus = {
      "stone": "🪨 Камень",
      "scissors": "✂️ Ножницы",
      "paper": "📄 Бумага",
  }

  await callback.message.edit_text(
      f"Игрок {callback.from_user.full_name} выбрал: {choices_rus[user_choice]}\n\n"
      "🤖 Бот думает над своим ходом..."
  )

  await asyncio.sleep(2)

  bot_choice = random.choice(["stone", "scissors", "paper"])

  if user_choice == bot_choice:
    result = "🤝 Ничья!"
    result_code = "DRAW"
  elif (
      (user_choice == "stone" and bot_choice == "scissors")
      or (user_choice == "scissors" and bot_choice == "paper")
      or (user_choice == "paper" and bot_choice == "stone")
  ):
    result = "🎉 Ты победил!"
    result_code = "WIN"
  else:
    result = "😢 Победил бот!"
    result_code = "LOSE"

  final_text = (
      f"🎮 Результаты игры:\n\n"
      f"👤 Игрок: {callback.from_user.full_name}\n"
      f"🎯 Твой выбор: {choices_rus[user_choice]}\n"
      f"🤖 Выбор бота: {choices_rus[bot_choice]}\n\n"
      f"{result}"
  )

  await callback.message.edit_text(final_text)

  user = callback.from_user
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"

  report_text = (
      "📊 Игра завершена!\n\n"
      f"👤 Игрок: {user_name} ({user_username})\n"
      f"🆔 ID: {user_id}\n"
      f"🎯 Выбор игрока: {choices_rus[user_choice]}\n"
      f"🤖 Выбор бота: {choices_rus[bot_choice]}\n"
      f"🏁 Итог: {result_code}"
  )

  contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="💬 Написать игроку", url=f"tg://user?id={user_id}"
      )
  ]])

  try:
    await bot.send_message(
        chat_id=MY_TELEGRAM_ID,
        text=report_text,
        reply_markup=contact_keyboard,
    )
  except Exception as e:
    logging.error(f"Не удалось отправить отчет админу: {e}")

  game_sessions.pop(user_id, None)
  await callback.answer()


async def main() -> None:
  bot = Bot(
      token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
  )

  await bot.delete_webhook(drop_pending_updates=True)

  logging.info("Бот успешно запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())
