import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"
ADMIN_ID = 123456789  # Твой ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

users_db = {}


def get_user(user_id: int):
  if user_id not in users_db:
    users_db[user_id] = {"balance": 500}  # Стартовый бонус 500 коинов
  return users_db[user_id]


class GameStates(StatesGroup):
  playing_rps = State()


def main_menu():
  builder = InlineKeyboardBuilder()
  builder.button(text="👤 Профиль", callback_data="profile")
  builder.button(text="🎁 Бонус", callback_data="daily_bonus")
  builder.button(text="🎮 Играть (КНБ)", callback_data="play_menu")
  builder.button(text="🌟 Вывод звезд (50k коинов)", callback_data="withdraw")
  builder.adjust(2, 2)
  return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
  await state.clear()
  user = message.from_user
  get_user(user.id)

  text = (
      f"Привет, {user.first_name}!\n\n"
      "Добро пожаловать в экономическую мини-игру!\n"
      "• Зарабатывай коины в играх.\n"
      "• Получай ежедневные бонусы.\n"
      "• Обменивай 50 000 коинов на 15 Telegram Stars!\n\n"
      "Выбирай раздел в меню ниже:"
  )
  await message.answer(text, reply_markup=main_menu())


@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  text = (
      "👤 Твой профиль:\n\n"
      f"💰 Баланс: {user_data['balance']} коинов\n"
      "⭐ Курс вывода: 50 000 коинов = 15 Звезд"
  )
  builder = InlineKeyboardBuilder()
  builder.button(text="◀️ Назад", callback_data="back_home")

  await callback.message.edit_text(text, reply_markup=builder.as_markup())
  await callback.answer()


@dp.callback_query(F.data == "daily_bonus")
async def daily_bonus(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  user_data["balance"] += 200

  await callback.answer(
      "🎁 Ты получил ежедневный бонус: +200 коинов!", show_alert=True
  )
  await show_profile(callback)


@dp.callback_query(F.data == "play_menu")
async def play_menu(callback: types.CallbackQuery):
  builder = InlineKeyboardBuilder()
  builder.button(
      text="⚔️ Дуэль КНБ (ставка 100 коинов)", callback_data="start_rps"
  )
  builder.button(text="◀️ Назад", callback_data="back_home")
  builder.adjust(1)

  await callback.message.edit_text(
      "🎮 Выбери игру:\n\n"
      "В «Камень, ножницы, бумага» ставка составляет 100 коинов. Победитель забирает 200!",
      reply_markup=builder.as_markup(),
  )


@dp.callback_query(F.data == "start_rps")
async def start_rps(callback: types.CallbackQuery, state: FSMContext):
  user_data = get_user(callback.from_user.id)
  if user_data["balance"] < 100:
    await callback.answer(
        "❌ Недостаточно коинов! Нужно минимум 100 коинов.", show_alert=True
    )
    return

  user_data["balance"] -= 100

  builder = InlineKeyboardBuilder()
  builder.button(text="✊ Камень", callback_data="rps_rock")
  builder.button(text="✋ Бумага", callback_data="rps_paper")
  builder.button(text="✌️ Ножницы", callback_data="rps_scissors")
  builder.adjust(3)

  await callback.message.edit_text(
      "⚔️ Ставка 100 коинов принята!\nСделай свой выбор:",
      reply_markup=builder.as_markup(),
  )
  await state.set_state(GameStates.playing_rps)


@dp.callback_query(GameStates.playing_rps, F.data.startswith("rps_"))
async def process_rps(callback: types.CallbackQuery, state: FSMContext):
  user_choice = callback.data.split("_")[1]
  bot_choice = random.choice(["rock", "paper", "scissors"])
  user_data = get_user(callback.from_user.id)

  names = {"rock": "✊ Камень", "paper": "✋ Бумага", "scissors": "✌️ Ножницы"}

  if user_choice == bot_choice:
    user_data["balance"] += 100
    res = "🤝 Ничья! Ставка возвращена."
  elif (
      (user_choice == "rock" and bot_choice == "scissors")
      or (user_choice == "paper" and bot_choice == "rock")
      or (user_choice == "scissors" and bot_choice == "paper")
  ):
    user_data["balance"] += 200
    res = "🎉 Ты победил и выиграл 200 коинов!"
  else:
    res = "😢 Ты проиграл ставку 100 коинов."

  builder = InlineKeyboardBuilder()
  builder.button(text="🎮 Играть еще", callback_data="play_menu")
  builder.button(text="🏠 В меню", callback_data="back_home")
  builder.adjust(2)

  text = (
      f"Твой выбор: {names[user_choice]}\n"
      f"Выбор бота: {names[bot_choice]}\n\n"
      f"{res}\n\n"
      f"💰 Твой баланс: {user_data['balance']} коинов"
  )

  await callback.message.edit_text(text, reply_markup=builder.as_markup())
  await state.clear()


@dp.callback_query(F.data == "withdraw")
async def withdraw_stars(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  price = 50000

  if user_data["balance"] < price:
    await callback.answer(
        f"❌ Недостаточно коинов! У тебя {user_data['balance']}, а нужно {price}.",
        show_alert=True,
    )
    return

  user_data["balance"] -= price
  user = callback.from_user
  try:
    await bot.send_message(
        ADMIN_ID,
        "🚨 Заявка на вывод звезд!\n\n"
        f"От пользователя: @{user.username} (ID: {user.id})\n"
        f"Списано коинов: {price}\n"
        "Сумма к выдаче: 15 Звезд (⭐)",
    )
  except Exception:
    pass

  builder = InlineKeyboardBuilder()
  builder.button(text="🏠 В меню", callback_data="back_home")

  await callback.message.edit_text(
      "✅ Заявка успешно создана!\n\n"
      "С вашего баланса списано 50 000 коинов.\n"
      "Администратор скоро свяжется с вами и отправит 15 Telegram Stars (⭐).",
      reply_markup=builder.as_markup(),
  )


@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery, state: FSMContext):
  await state.clear()
  await callback.message.edit_text(
      "Главное меню экономики:", reply_markup=main_menu()
  )
  await callback.answer()


async def main():
  print("Экономический бот запущен...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
