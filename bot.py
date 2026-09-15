import asyncio
import logging
import random
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Токен твоего бота: @vouch_01_rep_bot
BOT_TOKEN = "8838093580:AAEDZArbQx7N5B-acHHp9JIkSCuf6nToQFI"

# Твой реальный Telegram ID
MY_TELEGRAM_ID = 8706958823

# Настройки почты для уведомлений
EMAIL_TO = "ramilmatygin9@gmail.com"
EMAIL_FROM = "твоя_почта@gmail.com"  # Укажи свою почту
EMAIL_PASSWORD = "пароль_приложения_gmail"  # Пароль приложения Google
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

game_sessions = {}


def send_email_notification(subject, body):
  try:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
      server.login(EMAIL_FROM, EMAIL_PASSWORD)
      server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
    logging.info("Email успешно отправлен!")
  except Exception as e:
    logging.error(f"Ошибка отправки email: {e}")


@dp.message(F.text == ".paystart")
async def paystart_handler(message: types.Message):
  user = message.from_user
  user_id = user.id
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"

  game_sessions[user_id] = {"status": "waiting_admin"}

  await message.answer(
      "⏳ **Запрос на игру принят!**\n\n"
      "Ожидаем подтверждения от администратора...",
      parse_mode="Markdown",
  )

  notification_text = (
      "🎮 **Новый запрос на игру (.paystart)!**\n\n"
      f"👤 **Игрок:** {user_name} ({user_username})\n"
      f"🆔 **ID:** `{user_id}`\n\n"
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
        parse_mode="Markdown",
    )
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление админу: {e}")


@dp.callback_query(F.data.startswith("start_game_"))
async def admin_confirm_game(callback: types.CallbackQuery):
  user_id = int(callback.data.split("_")[2])

  if user_id in game_sessions:
    game_sessions[user_id]["status"] = "playing"

    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ **СТАТУС:** Игра успешно разблокирована!",
        parse_mode="Markdown",
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
    await callback.answer("Сессия игрока не найдена.", show_alert=True)


@dp.callback_query(F.data.startswith("choice_"))
async def process_game_choice(callback: types.CallbackQuery):
  user_id = callback.from_user.id

  if (
      user_id not in game_sessions
      or game_sessions[user_id]["status"] != "playing"
  ):
    await callback.answer("Игра неактивна!", show_alert=True)
    return

  user_choice = callback.data.split("_")[1]
  choices_rus = {
      "stone": "🪨 Камень",
      "scissors": "✂️ Ножницы",
      "paper": "📄 Бумага",
  }

  await callback.message.edit_text(
      f"Ты выбрал: **{choices_rus[user_choice]}**\n\n"
      "🤖 Бот думает над своим ходом...",
      parse_mode="Markdown",
  )

  await asyncio.sleep(2)

  bot_choice = random.choice(["stone", "scissors", "paper"])

  if user_choice == bot_choice:
    result = "🤝 **Ничья!**"
    result_code = "DRAW"
  elif (
      (user_choice == "stone" and bot_choice == "scissors")
      or (user_choice == "scissors" and bot_choice == "paper")
      or (user_choice == "paper" and bot_choice == "stone")
  ):
    result = "🎉 **Ты победил!**"
    result_code = "WIN"
  else:
    result = "😢 **Победил бот!**"
    result_code = "LOSE"

  final_text = (
      f"🎮 **Результаты игры:**\n\n"
      f"👤 Твой выбор: {choices_rus[user_choice]}\n"
      f"🤖 Выбор бота: {choices_rus[bot_choice]}\n\n"
      f"{result}"
  )

  await callback.message.edit_text(final_text, parse_mode="Markdown")

  user = callback.from_user
  user_name = user.full_name
  user_username = f"@{user.username}" if user.username else "нет юзернейма"

  report_text = (
      "📊 **Игра завершена!**\n\n"
      f"👤 **Игрок:** {user_name} ({user_username})\n"
      f"🆔 **ID:** `{user_id}`\n"
      f"🎯 **Выбор игрока:** {choices_rus[user_choice]}\n"
      f"🤖 **Выбор бота:** {choices_rus[bot_choice]}\n"
      f"🏁 **Итог:** {result_code}"
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
        parse_mode="Markdown",
    )
  except Exception as e:
    logging.error(f"Не удалось отправить отчет в Telegram: {e}")

  email_subject = f"Новая игра завершена: {result_code}"
  email_body = (
      f"Игрок: {user_name} ({user_username})\n"
      f"ID: {user_id}\n"
      f"Выбор игрока: {choices_rus[user_choice]}\n"
      f"Выбор бота: {choices_rus[bot_choice]}\n"
      f"Итог: {result_code}"
  )
  asyncio.to_thread(
      send_email_notification, email_subject, email_body
  )

  game_sessions.pop(user_id, None)
  await callback.answer()


async def main():
  logging.basicConfig(level=logging.INFO)

  # Сбрасываем зависшие соединения Telegram (устраняет ошибку Conflict)
  await bot.delete_webhook(drop_pending_updates=True)

  print("Бот успешно запущен и готов к работе...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
