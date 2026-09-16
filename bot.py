import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Токен твоего бота
TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище активных игр в чатах
group_games = {}


class ChatGameStates(StatesGroup):
  waiting_for_players = State()
  waiting_for_moves = State()


# Обработка команды .starts (и /starts)
@dp.message(
    F.chat.type.in_({"group", "supergroup"}),
    (F.text == ".starts") | Command("starts"),
)
async def start_group_game(message: types.Message, state: FSMContext):
  chat_id = message.chat.id
  user = message.from_user

  builder = InlineKeyboardBuilder()
  builder.button(text="🎮 Принять вызов", callback_data="accept_game")

  group_games[chat_id] = {
      "p1": user.id,
      "p1_name": user.first_name,
      "p2": None,
      "p2_name": None,
      "moves": {},
  }

  await message.answer(
      f"🎯 **{user.first_name}** создал игру «Камень, ножницы, бумага»!\n\n"
      "Кто готов составить компанию? Нажми кнопку ниже:",
      reply_markup=builder.as_markup(),
      parse_mode="Markdown",
  )
  await state.set_state(ChatGameStates.waiting_for_players)


# Принятие вызова вторым игроком
@dp.callback_query(
    ChatGameStates.waiting_for_players, F.data == "accept_game"
)
async def accept_game(callback: types.CallbackQuery, state: FSMContext):
  chat_id = callback.message.chat.id
  user = callback.from_user

  if chat_id not in group_games:
    await callback.answer(
        "Эта игра уже устарела или отменена.", show_alert=True
    )
    return

  game = group_games[chat_id]

  if user.id == game["p1"]:
    await callback.answer("Ты не можешь играть сам с собой!", show_alert=True)
    return

  game["p2"] = user.id
  game["p2_name"] = user.first_name

  builder = InlineKeyboardBuilder()
  builder.button(text="✊ Камень", callback_data="gmove_rock")
  builder.button(text="✋ Бумага", callback_data="gmove_paper")
  builder.button(text="✌️ Ножницы", callback_data="gmove_scissors")
  builder.adjust(3)

  await callback.message.edit_text(
      f"🎉 Соперник найден!\n"
      f"Дуэль: **{game['p1_name']}** VS **{game['p2_name']}**\n\n"
      "Сделайте свои ходы (каждый нажимает кнопку для себя):",
      reply_markup=builder.as_markup(),
      parse_mode="Markdown",
  )
  await state.set_state(ChatGameStates.waiting_for_moves)


# Обработка ходов
@dp.callback_query(ChatGameStates.waiting_for_moves, F.data.startswith("gmove_"))
async def process_group_move(callback: types.CallbackQuery, state: FSMContext):
  chat_id = callback.message.chat.id
  user_id = callback.from_user.id

  if chat_id not in group_games:
    await callback.answer("Игра не найдена.", show_alert=True)
    return

  game = group_games[chat_id]

  if user_id != game["p1"] and user_id != game["p2"]:
    await callback.answer("Ты не участник этой дуэли!", show_alert=True)
    return

  if user_id in game["moves"]:
    await callback.answer(
        "Ты уже сделал свой ход! Жди соперника.", show_alert=True
    )
    return

  move = callback.data.split("_")[1]
  game["moves"][user_id] = move
  await callback.answer("Ход принят! 🤫")

  if len(game["moves"]) == 2:
    p1 = game["p1"]
    p2 = game["p2"]
    m1 = game["moves"][p1]
    m2 = game["moves"][p2]

    names = {
        "rock": "✊ Камень",
        "paper": "✋ Бумага",
        "scissors": "✌️ Ножницы",
    }

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
    group_games.pop(chat_id, None)
    await state.clear()
  else:
    waiting_for = (
        game["p2_name"] if user_id == game["p1"] else game["p1_name"]
    )
    await callback.message.edit_text(
        f"Дуэль: **{game['p1_name']}** VS **{game['p2_name']}**\n\n"
        f"✅ Один игрок уже сделал ход.\n"
        f"⏳ Ожидаем ход от игрока: **{waiting_for}**",
        parse_mode="Markdown",
    )


async def main():
  print("Бот запущен и готов к работе...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
