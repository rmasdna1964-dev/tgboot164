import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Токен твоего бота
TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Состояния для групповой игры
class ChatGameStates(StatesGroup):
  waiting_for_players = State()
  waiting_for_moves = State()


# Хранение активных игр по ID чата
# {chat_id: {"p1": user_id_1, "p1_name": name, "p2": user_id_2, "p2_name": name, "moves": {}}}
group_games = {}


# Команда .starts (и /starts на всякий случай)
@dp.message_handler(commands=["starts"], chat_type=["group", "supergroup"], state="*")
@dp.message_handler(
    lambda msg: msg.text and msg.text.startswith(".starts"),
    chat_type=["group", "supergroup"],
    state="*",
)
async def start_group_game(message: types.Message, state: FSMContext):
  chat_id = message.chat.id
  user = message.from_user

  keyboard = InlineKeyboardMarkup()
  keyboard.add(
      InlineKeyboardButton("🎮 Принять вызов", callback_data="accept_game")
  )

  # Сохраняем первого игрока (создателя)
  group_games[chat_id] = {
      "p1": user.id,
      "p1_name": user.first_name,
      "p2": None,
      "p2_name": None,
      "moves": {},
  }

  await message.answer(
      f"🎯 **{user.first_name}** создал игру «Камень, ножницы, бумага»!\n\n"
      "Кто готов составить компанию? Нажмите кнопку ниже:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await ChatGameStates.waiting_for_players.set()


# Второй игрок принимает вызов
@dp.callback_query_handler(
    lambda c: c.data == "accept_game", state=ChatGameStates.waiting_for_players
)
async def accept_game(callback: types.CallbackQuery, state: FSMContext):
  chat_id = callback.message.chat.id
  user = callback.from_user

  if chat_id not in group_games:
    await callback.answer("Эта игра уже устарела или отменена.", show_alert=True)
    return

  game = group_games[chat_id]

  # Защита, чтобы создатель не играл сам с собой
  if user.id == game["p1"]:
    await callback.answer("Ты не можешь играть сам с собой!", show_alert=True)
    return

  game["p2"] = user.id
  game["p2_name"] = user.first_name

  # Клавиатура с выбором хода
  keyboard = InlineKeyboardMarkup(row_width=3)
  keyboard.add(
      InlineKeyboardButton("✊ Камень", callback_data="gmove_rock"),
      InlineKeyboardButton("✋ Бумага", callback_data="gmove_paper"),
      InlineKeyboardButton("✌️ Ножницы", callback_data="gmove_scissors"),
  )

  await callback.message.edit_text(
      f"🎉 Соперник найден!\n"
      f"Дуэль: **{game['p1_name']}** VS **{game['p2_name']}**\n\n"
      "Сделайте свои ходы (нажмите кнопку ниже, каждый выбирает для себя):",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await ChatGameStates.waiting_for_moves.set()


# Обработка ходов игроков в чате
@dp.callback_query_handler(
    lambda c: c.data.startswith("gmove_"), state=ChatGameStates.waiting_for_moves
)
async def process_group_move(callback: types.CallbackQuery, state: FSMContext):
  chat_id = callback.message.chat.id
  user_id = callback.from_user.id

  if chat_id not in group_games:
    await callback.answer("Игра не найдена.", show_alert=True)
    return

  game = group_games[chat_id]

  # Проверяем, участвует ли этот пользователь в игре
  if user_id != game["p1"] and user_id != game["p2"]:
    await callback.answer("Ты не участник этой дуэли!", show_alert=True)
    return

  move = callback.data.split("_")[1]

  # Проверяем, не ходил ли он уже
  if user_id in game["moves"]:
    await callback.answer("Ты уже сделал свой ход! Жди соперника.", show_alert=True)
    return

  # Сохраняем ход
  game["moves"][user_id] = move
  await callback.answer("Ход принят! 🤫")

  # Проверяем, оба ли походили
  if len(game["moves"]) == 2:
    p1 = game["p1"]
    p2 = game["p2"]
    m1 = game["moves"][p1]
    m2 = game["moves"][p2]

    names = {"rock": "✊ Камень", "paper": "✋ Бумага", "scissors": "✌️ Ножницы"}

    # Логика определения победителя
    if m1 == m2:
      result_text = "🤝 **Ничья!** Победителя нет."
    elif (
        (m1 == "rock" and m2 == "scissors")
        or (m1 == "paper" and m2 == "rock")
        or (m1 == "scissors" and m2 == "paper")
    ):
      result_text = f"🏆 Победил **{game['p1_name']}**! 🎉"
    else:
      result_text = f"🏆 Победил **{game['p2_name']}**! 🎉"

    final_text = (
        f"⚔️ **ИТОГИ ДУЭЛИ** ⚔️\n\n"
        f"👤 {game['p1_name']}: {names[m1]}\n"
        f"👤 {game['p2_name']}: {names[m2]}\n\n"
        f"{result_text}"
    )

    await callback.message.edit_text(final_text, parse_mode="Markdown")

    # Очищаем игру
    group_games.pop(chat_id, None)
    await state.finish()
  else:
    # Обновляем сообщение, чтобы показать, кто походил
    waiting_for = (
        game["p2_name"] if user_id == game["p1"] else game["p1_name"]
    )
    await callback.message.edit_text(
        f"Дуэль: **{game['p1_name']}** VS **{game['p2_name']}**\n\n"
        f"✅ Один игрок уже сделал ход.\n"
        f"⏳ Ожидаем ход от игрока: **{waiting_for}**",
        parse_mode="Markdown",
    )


if __name__ == "__main__":
  from aiogram import executor

  print("Бот для чатов запущен...")
  executor.start_polling(dp, skip_updates=True)
