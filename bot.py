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
# Баланс игроков: { user_id: balance }
balances = {}


def get_balance(user_id: int) -> int:
  if user_id not in balances:
    balances[user_id] = 50  # Стартовый баланс коинов
  return balances[user_id]


@dp.message(F.text.in_({".paystart", "/paystart"}))
async def paystart_handler(message: types.Message, bot: Bot):
  user = message.from_user
  user_id = user.id
  user_name = user.full_name
  chat_id = message.chat.id

  # Проверяем баланс
  current_bal = get_balance(user_id)
  if current_bal < 5:
    await message.answer(
        "❌ У вас недостаточно коинов для игры! (Нужно минимум 5 коинов)."
    )
    return

  games[user_id] = {
      "status": "waiting_guest",
      "host_id": user_id,
      "host_name": user_name,
      "guest_id": None,
      "guest_name": None,
      "chat_id": chat_id,
      "host_choice": None,
      "guest_choice": None,
  }

  join_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="🎮 Принять вызов (Войти)", callback_data=f"join_{user_id}"
      )
  ]])

  await message.answer(
      f"⚔️ <b>{user_name}</b> создал(а) дуэль в Камень, ножницы, бумага!\n"
      f"💰 Ваш баланс: <b>{current_bal} коинов</b> (Победа: +10 | Проигрыш:"
      " -5)\n\n"
      "⏳ Ждем второго игрока...",
      reply_markup=join_keyboard,
  )


@dp.callback_query(F.data.startswith("join_"))
async def join_game(callback: types.CallbackQuery, bot: Bot):
  host_id = int(callback.data.split("_")[1])
  guest = callback.from_user

  if host_id not in games or games[host_id]["status"] != "waiting_guest":
    await callback.answer("Эта игра уже началась или отменена!", show_alert=True)
    return

  if guest.id == host_id:
    await callback.answer("Нельзя играть самому с собой!", show_alert=True)
    return

  guest_bal = get_balance(guest.id)
  if guest_bal < 5:
    await callback.answer(
        "У вас меньше 5 коинов, вы не можете войти в игру!", show_alert=True
    )
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
      f"🔥 <b>Дуэль началась!</b>\n"
      f"👤 {games[host_id]['host_name']} vs 👤 {guest.full_name}\n\n"
      "⏱ Сделайте свой выбор ниже:",
      reply_markup=choice_keyboard,
  )
  await callback.answer("Вы вошли в игру!")


@dp.callback_query(F.data.startswith("move_"))
async def process_move(callback: types.CallbackQuery, bot: Bot):
  parts = callback.data.split("_")
  host_id = int(parts[1])
  move = parts[2]

  if host_id not in games or games[host_id]["status"] != "playing":
    await callback.answer("Игра неактивна!", show_alert=True)
    return

  game = games[host_id]
  user_id = callback.from_user.id

  if user_id != game["host_id"] and user_id != game["guest_id"]:
    await callback.answer("Вы не участник этой игры!", show_alert=True)
    return

  choices_rus = {
      "stone": "🪨 Камень",
      "scissors": "✂️ Ножницы",
      "paper": "📄 Бумага",
  }

  if user_id == game["host_id"]:
    if game["host_choice"] is not None:
      await callback.answer("Вы уже сделали выбор!", show_alert=True)
      return
    game["host_choice"] = move
  else:
    if game["guest_choice"] is not None:
      await callback.answer("Вы уже сделали выбор!", show_alert=True)
      return
    game["guest_choice"] = move

  await callback.answer(f"Вы выбрали: {choices_rus[move]}")

  # Если оба сделали ходы
  if game["host_choice"] and game["guest_choice"]:
    h_choice = game["host_choice"]
    g_choice = game["guest_choice"]
    host_id_real = game["host_id"]
    guest_id_real = game["guest_id"]

    # Логика победителя
    if h_choice == g_choice:
      res_text = "🤝 Ничья! Коины на месте."
    elif (
        (h_choice == "stone" and g_choice == "scissors")
        or (h_choice == "scissors" and g_choice == "paper")
        or (h_choice == "paper" and g_choice == "stone")
    ):
      balances[host_id_real] = get_balance(host_id_real) + 10
      balances[guest_id_real] = max(0, get_balance(guest_id_real) - 5)
      res_text = (
          f"🎉 Победил(а) {game['host_name']}! (+10 коинов)\n💔"
          f" {game['guest_name']} проиграл(а) (-5 коинов)"
      )
    else:
      balances[guest_id_real] = get_balance(guest_id_real) + 10
      balances[host_id_real] = max(0, get_balance(host_id_real) - 5)
      res_text = (
          f"🎉 Победил(а) {game['guest_name']}! (+10 коинов)\n💔"
          f" {game['host_name']} проиграл(а) (-5 коинов)"
      )

    h_bal = get_balance(host_id_real)
    g_bal = get_balance(guest_id_real)

    final_msg = (
        "🏁 <b>Итоги дуэли!</b>\n\n"
        f"👤 {game['host_name']}: {choices_rus[h_choice]} (Баланс: {h_bal}"
        " коинов)\n"
        f"👤 {game['guest_name']}: {choices_rus[g_choice]} (Баланс: {g_bal}"
        " коинов)\n\n"
        f"<b>{res_text}</b>"
    )

    if h_bal >= 30:
      final_msg += f"\n\n🏆 <b>{game['host_name']} набрал(а) 30 коинов и выиграл(а) матч!</b>"
      balances[host_id_real] = 50
      balances[guest_id_real] = 50
    elif g_bal >= 30:
      final_msg += f"\n\n🏆 <b>{game['guest_name']} набрал(а) 30 коинов и выиграл(а) матч!</b>"
      balances[host_id_real] = 50
      balances[guest_id_real] = 50

    try:
      await callback.message.edit_text(final_msg)
    except Exception:
      pass

    games.pop(host_id, None)
  else:
    try:
      await callback.message.edit_text(
          f"✅ Ваш выбор принят ({choices_rus[move]}).\n⏳ Ждем ход второго"
          " игрока..."
      )
    except Exception:
      pass


async def main() -> None:
  bot = Bot(
      token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
  )
  await bot.delete_webhook(drop_pending_updates=True)
  logging.info("Бот запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())
