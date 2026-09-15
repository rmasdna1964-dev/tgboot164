import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Токен первого бота (Игровой бот): @vouch_01_rep_bot
SHOP_TOKEN = "8838093580:AAEDZArbQx7N5B-acHHp9JIkSCuf6nToQFI"

# Токен второго бота (Секретарь / Админ-бот)
ADMIN_BOT_TOKEN = "8623258820:AAEInCHPfQXtgMcW6i5Ftt07ewy9JXFlxaE"

# Твой реальный Telegram ID
MY_TELEGRAM_ID = 8706958823

bot_shop = Bot(token=SHOP_TOKEN)
bot_admin_sender = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()

# Словарь для отслеживания состояния игр игроков
# Ключ: user_id, Значение: {"status": "waiting_admin" / "playing" / "finished", "choice": None}
game_sessions = {}


# Команда .paystart для запуска игры
@dp.message(F.text == ".paystart")
async def paystart_handler(message: types.Message):
  user = message.from_user
  user_id = user.id
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"

  # Инициализируем сессию игрока (игра ждет подтверждения от админа)
  game_sessions[user_id] = {"status": "waiting_admin", "choice": None}

  await message.answer(
      "⏳ **Запрос на игру принят!**\n\n"
      "Ожидаем подтверждения от администратора (секретаря)... Как только админ подтвердит, игра начнется!",
      parse_mode="Markdown",
  )

  # Формируем уведомление для тебя на второго бота
  notification_text = (
      "🎮 **Новый запрос на игру (.paystart)!**\n\n"
      f"👤 **Игрок:** {user_name} ({user_username})\n"
      f"🆔 **ID:** `{user_id}`\n\n"
      "Нажми кнопку ниже, чтобы разрешить игроку начать:"
  )

  # Кнопка подтверждения старта
  admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="✅ Подтвердить старт игры", callback_data=f"start_game_{user_id}"
      )
  ]])

  try:
    await bot_admin_sender.send_message(
        chat_id=MY_TELEGRAM_ID,
        text=notification_text,
        reply_markup=admin_keyboard,
        parse_mode="Markdown",
    )
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление админу: {e}")


# Обработка нажатия на кнопку "Подтвердить старт игры" во втором боте (прилетает в ЛС админу)
@dp.callback_query(F.data.startswith("start_game_"))
async def admin_confirm_game(callback: types.CallbackQuery):
  # Извлекаем ID игрока из callback_data
  user_id = int(callback.data.split("_")[2])

  if user_id in game_sessions:
    game_sessions[user_id]["status"] = "playing"

    # Уведомляем тебя, что игра запущена
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ **СТАТУС:** Игра успешно разблокирована для игрока!",
        parse_mode="Markdown",
    )
    await callback.answer("Игра подтверждена!")

    # Отправляем игроку клавиатуру для выбора в первом боте
    game_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪨 Камень", callback_data="choice_stone"),
            InlineKeyboardButton(text="✂️ Ножницы", callback_data="choice_scissors"),
        ],
        [InlineKeyboardButton(text="📄 Бумага", callback_data="choice_paper")],
    ])

    try:
      await bot_shop.send_message(
          chat_id=user_id,
          text=(
              "🟢 **Администратор подтвердил старт!**\n\n"
              "Игра началась! Выбери свой вариант:"
          ),
          reply_markup=game_keyboard,
          parse_mode="Markdown",
      )
    except Exception as e:
      logging.error(f"Не удалось отправить сообщение игроку: {e}")
  else:
    await callback.answer("Сессия игрока не найдена или устарела.", show_alert=True)


# Обработка выбора игрока (Камень, Ножницы, Бумага)
@dp.callback_query(F.data.startswith("choice_"))
async def process_game_choice(callback: types.CallbackQuery):
  user_id = callback.from_user.id

  if (
      user_id not in game_sessions
      or game_sessions[user_id]["status"] != "playing"
  ):
    await callback.answer("Игра еще не началась или уже завершена!", show_alert=True)
    return

  user_choice = callback.data.split("_")[1]  # stone, scissors, paper
  choices_rus = {
      "stone": "🪨 Камень",
      "scissors": "✂️ Ножницы",
      "paper": "📄 Бумага",
  }

  # Меняем сообщение на статус ожидания (ждем 2 секунды)
  await callback.message.edit_text(
      f"Ты выбрал: **{choices_rus[user_choice]}**\n\n"
      "🤖 Бот думает над своим ходом...",
      parse_mode="Markdown",
  )

  # Ждем ровно 2 секунды для создания интриги
  await asyncio.sleep(2)

  # Ход бота (случайный выбор)
  bot_choice = random.choice(["stone", "scissors", "paper"])

  # Логика определения победителя
  if user_choice == bot_choice:
    result = "🤝 **Ничья!**"
    result_code = "draw"
  elif (
      (user_choice == "stone" and bot_choice == "scissors")
      or (user_choice == "scissors" and bot_choice == "paper")
      or (user_choice == "paper" and bot_choice == "stone")
  ):
    result = "🎉 **Ты победил!**"
    result_code = "win"
  else:
    result = "😢 **Победил бот!**"
    result_code = "lose"

  final_text = (
      f"🎮 **Результаты игры:**\n\n"
      f"👤 Твой выбор: {choices_rus[user_choice]}\n"
      f"🤖 Выбор бота: {choices_rus[bot_choice]}\n\n"
      f"{result}"
  )

  await callback.message.edit_text(final_text, parse_mode="Markdown")

  # Собираем данные игрока для финального отчета тебе
  user = callback.from_user
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"

  report_text = (
      "📊 **Игра завершена!**\n\n"
      f"👤 **Игрок:** {user_name} ({user_username})\n"
      f"🆔 **ID:** `{user_id}`\n"
      f"🎯 **Выбор игрока:** {choices_rus[user_choice]}\n"
      f"🤖 **Выбор бота:** {choices_rus[bot_choice]}\n"
      f"🏁 **Итог:** {result_code.upper()}"
  )

  # Кнопка для связи с этим конкретным игроком
  contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="💬 Написать игроку", url=f"tg://user?id={user_id}"
      )
  ]])

  # Отправляем тебе отчет во второй бот
  try:
    await bot_admin_sender.send_message(
        chat_id=MY_TELEGRAM_ID,
        text=report_text,
        reply_markup=contact_keyboard,
        parse_mode="Markdown",
    )
  except Exception as e:
    logging.error(f"Не удалось отправить итоговый отчет админу: {e}")

  # Завершаем сессию
  game_sessions.pop(user_id, None)
  await callback.answer()


async def main():
  logging.basicConfig(level=logging.INFO)
  await bot_shop.delete_webhook(drop_pending_updates=True)
  print("Бот 'Камень, ножницы, бумага' запущен и ожидает .paystart...")
  await dp.start_polling(bot_shop)


if __name__ == "__main__":
  asyncio.run(main())
