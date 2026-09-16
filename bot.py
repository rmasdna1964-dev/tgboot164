import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Токен твоего бота
TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


# Состояния для конечного автомата (FSM) игры
class GameState(StatesGroup):
  waiting_for_choice = State()


# Словарь для красивого отображения ходов
CHOICES = {
    "rock": {"name": "✊ Камень", "emoji": "✊"},
    "paper": {"name": "✋ Бумага", "emoji": "✋"},
    "scissors": {"name": "✌️ Ножницы", "emoji": "✌️"},
}


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
  await state.clear()
  user_name = message.from_user.first_name
  welcome_text = (
      f"Привет, **{user_name}**! 👋\n\n"
      "Добро пожаловать в игру **Камень, ножницы, бумага**!\n"
      "Я буду твоим соперником. Сыграем?\n\n"
      "Нажми кнопку ниже, чтобы сделать свой ход!"
  )

  # Создаем инлайн-клавиатуру с выбором
  builder = InlineKeyboardBuilder()
  builder.button(
      text="✊ Камень", callback_data="game_rock"
  )
  builder.button(text="✋ Бумага", callback_data="game_paper")
  builder.button(text="✌️ Ножницы", callback_data="game_scissors")
  builder.adjust(3)  

  await message.answer(
      welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown"
  )
  await state.set_state(GameState.waiting_for_choice)


# Обработчик нажатия на кнопки игры
@dp.callback_query(
    GameState.waiting_for_choice, F.data.startswith("game_")
)
async def process_game_choice(callback: types.CallbackQuery, state: FSMContext):
  user_choice = callback.data.split("_")[1]  # rock, paper или scissors
  bot_choice = random.choice(["rock", "paper", "scissors"])

  user_data = CHOICES[user_choice]
  bot_data = CHOICES[bot_choice]

  # Логика определения победителя
  if user_choice == bot_choice:
    result_text = "🤝 **Ничья!**"
  elif (
      (user_choice == "rock" and bot_choice == "scissors")
      or (user_choice == "paper" and bot_choice == "rock")
      or (user_choice == "scissors" and bot_choice == "paper")
  ):
    result_text = "🎉 **Ты победил!**"
  else:
    result_text = "🤖 **Я победил!**"

  # Формируем сообщение с итогами раунда
  response_text = (
      f"Твой ход: {user_data['name']}\n"
      f"Мой ход: {bot_data['name']}\n\n"
      f"{result_text}\n\n"
      "Хочешь сыграть еще раз? Жми кнопку!"
  )

  # Кнопка для повторной игры
  builder = InlineKeyboardBuilder()
  builder.button(text="✊ Камень", callback_data="game_rock")
  builder.button(text="✋ Бумага", callback_data="game_paper")
  builder.button(text="✌️ Ножницы", callback_data="game_scissors")
  builder.adjust(3)

  # Редактируем сообщение, чтобы не засорять чат
  await callback.message.edit_text(
      response_text, reply_markup=builder.as_markup(), parse_mode="Markdown"
  )
  await callback.answer()


# Главная функция запуска поллинга
async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
