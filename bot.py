import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"

dp = Dispatcher()
games = {}
balances = {}  # { user_id: balance }


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

  current_bal = get_balance(user_id)
  if current_bal < 5:
    await message.answer(
        "❌ <b>Недостаточно средств!</b>\nДля создания дуэли нужно минимум"
        " <code>5 коинов</code>."
    )
    return

  games[user_id] = {
      "status": "waiting_guest",
      "host_id": user_id,
      "host_name": user_name,
      "chat_id": chat_id,
      "guest_id": None,
      "guest_name": None,
      "host_choice": None,
      "guest_choice": None,
  }

  join_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(
          text="🎮 Принять вызов и войти", callback_data=f"join_{user_id}"
      )
  ]])

  text = (
      f"⚔️ <b>ДУЭЛЬ: КАМЕНЬ, НОЖНИЦЫ, БУМАГА</b> ⚔️\n\n"
      f"👤 <b>Создатель:</b> {user_name}\n"
      f"💰 <b>Твой баланс:</b> <code>{current_bal} коинов</code>\n"
      f"📊 <b>Правила:</b> Победа <code>+10</code> | Проигрыш <code>-5</code> |"
      " Игра до <code>30</code> коинов\n\n"
      "⏳ <i>Ожидание второго игрока... Нажми кнопку ниже, чтобы"
      " присоединиться!</i>"
  )

  await message.answer(text, reply_markup=join_keyboard)


@dp.callback_query(F.data.startswith("join_"))
async def join_game(callback: types.CallbackQuery, bot: Bot):
  host_id = int(callback.data.split("_")[1])
  guest = callback.from_user

  if host_id not in games or games[host_id]["status"] != "waiting_guest":
    await callback.answer(
        "⚠️ Эта игра уже началась или была отменена!", show_alert=True
    )
    return

  if guest.id == host_id:
    await callback.answer("⚠️ Нельзя играть против самого себя!", show_alert=True)
    return

  guest_bal = get_balance(guest.id)
  if guest_bal < 5:
    await callback.answer(
        "⚠️ У вас меньше 5 коинов для участия!", show_alert=True
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

  host_name = games[host_id]["host_name"]
  guest_name = guest.full_name

  text = (
      f"🔥 <b>БИТВА НАЧАЛАСЬ!</b> 🔥\n\n"
      f"🥊 <b>{host_name}</b>  VS  <b>{guest_name}</b>\n\n"
      "👇 <b>Сделайте ваш выбор прямо сейчас:</b>"
  )

  # Редактируем сообщение, чтобы у всех появились кнопки выбора
  await callback.message.edit_text(text, reply_markup=choice_keyboard)
  await callback.answer("✅ Вы успешно вошли в игру!")


@dp.callback_query(F.data.startswith("move_"))
async def process_move(callback: types.CallbackQuery, bot: Bot):
  parts = callback.data.split("_")
  host_id = int(parts[1])
  move = parts[2]

  if host_id not in games or games[host_id]["status"] != "playing":
    await callback.answer("⚠️ Эта игра уже завершена!", show_alert=True)
    return

  game = games[host_id]
  user_id = callback.from_user.id

  if user_id != game["host_id"] and user_id != game["guest_id"]:
    await callback.answer(
        "⚠️ Вы не являетесь участником этой дуэли!", show_alert=True
    )
    return

  choices_rus = {
      "stone": "🪨 Камень",
      "scissors": "✂️ Ножницы",
      "paper": "📄 Бумага",
  }

  if user_id == game["host_id"]:
    if game["host_choice"] is not None:
      await callback.answer("⚠️ Вы уже сделали свой выбор!", show_alert=True)
      return
    game["host_choice"] = move
  else:
    if game["guest_choice"] is not None:
      await callback.answer("⚠️ Вы уже сделали свой выбор!", show_alert=True)
      return
    game["guest_choice"] = move

  await callback.answer(f"Вы выбрали: {choices_rus[move]}")

  # Проверяем, сделали ли оба игрока ход
  if game["host_choice"] and game["guest_choice"]:
    h_choice = game["host_choice"]
    g_choice = game["guest_choice"]
    h_id = game["host_id"]
    g_id = game["guest_id"]

    # Логика определения победителя
    if h_choice == g_choice:
      res_text = "🤝 <b>НИЧЬЯ!</b> Никто не получает и не теряет коины."
      winner = None
    elif (
        (h_choice == "stone" and g_choice == "scissors")
        or (h_choice == "scissors" and g_choice == "paper")
        or (h_choice == "paper" and g_choice == "stone")
    ):
      balances[h_id] = get_balance(h_id) + 10
      balances[g_id] = max(0, get_balance(g_id) - 5)
      res_text = (
          f"🎉 <b>Победитель раунда: {game['host_name']}!</b>\n💰"
          f" <code>{game['host_name']}</code>: +10 коинов\n💔"
          f" <code>{game['guest_name']}</code>: -5 коинов"
      )
    else:
      balances[g_id] = get_balance(g_id) + 10
      balances[h_id] = max(0, get_balance(h_id) - 5)
      res_text = (
          f"🎉 <b>Победитель раунда: {game['guest_name']}!</b>\n💰"
          f" <code>{game['guest_name']}</code>: +10 коинов\n💔"
          f" <code>{game['host_name']}</code>: -5 коинов"
      )

    h_bal = get_balance(h_id)
    g_bal = get_balance(g_id)

    final_msg = (
        f"🏁 <b>ИТОГИ ДУЭЛИ</b> 🏁\n\n"
        f"👤 <b>{game['host_name']}</b> выбрал: {choices_rus[h_choice]}\n"
        f"👤 <b>{game['guest_name']}</b> выбрал: {choices_rus[g_choice]}\n\n"
        f"───────────────────\n"
        f"{res_text}\n\n"
        f"📊 <b>Текущий баланс:</b>\n"
        f"• {game['host_name']}: <code>{h_bal} коинов</code>\n"
        f"• {game['guest_name']}: <code>{g_bal} коинов</code>"
    )

    # Проверка победы в матче до 30 коинов
    if h_bal >= 30:
      final_msg += (
          f"\n\n🏆 <b>ТРИУМФ! {game['host_name']} набрал(а) 30 коинов и выиграл(а)"
          " игру!</b> 👑"
      )
      balances[h_id] = 50
      balances[g_id] = 50
    elif g_bal >= 30:
      final_msg += (
          f"\n\n🏆 <b>ТРИУМФ! {game['guest_name']} набрал(а) 30 коинов и выиграл(а)"
          " игру!</b> 👑"
      )
      balances[h_id] = 50
      balances[g_id] = 50

    try:
      await callback.message.edit_text(final_msg)
    except Exception:
      pass

    games.pop(host_id, None)
  else:
    # Сообщаем, чей ход принят, а кого еще ждем
    waiting_person = (
        game["guest_name"] if user_id == game["host_id"] else game["host_name"]
    )
    try:
      await callback.message.edit_text(
          f"✅ <b>Ваш ход принят!</b> ({choices_rus[move]})\n\n⏳ Ожидаем выбор"
          f" игрока <b>{waiting_person}</b>..."
      )
    except Exception:
      pass


async def main() -> None:
  bot = Bot(
      token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
  )
  await bot.delete_webhook(drop_pending_updates=True)
  logging.info("Стильный бот для дуэлей успешно запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())
