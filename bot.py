import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8838093580:AAFqx0JsQfxnZLk1h9--4JhXF-FY0U6U-cQ"
ADMIN_ID = 123456789  # Твой реальный Telegram ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

users_db = {}


def get_user(user_id: int):
  if user_id not in users_db:
    users_db[user_id] = {
        "balance": 500,
        "last_bonus": 0,  # Время последнего получения бонуса
    }
  return users_db[user_id]


class GameStates(StatesGroup):
  playing_rps = State()
  playing_dice_choice = State()
  playing_basket = State()


# Главное меню
def main_menu():
  builder = InlineKeyboardBuilder()
  builder.button(text="👤 Мой профиль", callback_data="profile")
  builder.button(text="🎁 Ежедневный бонус (24ч)", callback_data="daily_bonus")
  builder.button(text="⚔️ Дуэль КНБ (100 коинов)", callback_data="start_rps")
  builder.button(text="🎲 Кости (Угадай число)", callback_data="menu_dice")
  builder.button(text="🏀 Баскетбол (Попади в кольцо)", callback_data="menu_basket")
  builder.button(text="🌟 Вывод 15 Звезд (50k)", callback_data="withdraw")
  builder.adjust(1, 1, 1, 1, 1, 1)
  return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
  await state.clear()
  user = message.from_user
  get_user(user.id)

  text = (
      f"Добро пожаловать в Arcade & Crypto Hub, {user.first_name}!\n\n"
      "Здесь ты можешь испытать удачу в крутых мини-играх, поднять банк и вывести"
      " реальные Telegram Stars! ⭐\n\n"
      "Выбери режим в меню ниже:"
  )
  await message.answer(text, reply_markup=main_menu())


@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  text = (
      "Твой игровой профиль:\n\n"
      f"Баланс: {user_data['balance']} коинов\n"
      "Курс обмена: 50 000 коинов = 15 Telegram Stars"
  )
  builder = InlineKeyboardBuilder()
  builder.button(text="◀️ Назад в меню", callback_data="back_home")

  await callback.message.edit_text(text, reply_markup=builder.as_markup())
  await callback.answer()


# ================= ЕЖЕДНЕВНЫЙ БОНУС (24 ЧАСА) =================
@dp.callback_query(F.data == "daily_bonus")
async def daily_bonus(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  user_data = get_user(user_id)

  current_time = time.time()
  cooldown = 24 * 60 * 60  # 24 часа в секундах
  time_passed = current_time - user_data["last_bonus"]

  if time_passed < cooldown:
    # Считаем, сколько осталось ждать
    left_seconds = int(cooldown - time_passed)
    hours = left_seconds // 3600
    minutes = (left_seconds % 3600) // 60
    await callback.answer(
        f"⏳ Ежедневный бонус еще не доступен!\nПриходите через {hours} ч."
        f" {minutes} мин.",
        show_alert=True,
    )
    return

  # Выдаем бонус
  user_data["last_bonus"] = current_time
  bonus_amount = 300
  user_data["balance"] += bonus_amount

  await callback.answer(
      f"🎁 Успешно! Вы забрали ежедневный бонус: +{bonus_amount} коинов!",
      show_alert=True,
  )
  await show_profile(callback)


@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery, state: FSMContext):
  await state.clear()
  await callback.message.edit_text(
      "Главное меню игрового центра:", reply_markup=main_menu()
  )
  await callback.answer()


# ================= КНБ =================
@dp.callback_query(F.data == "start_rps")
async def start_rps(callback: types.CallbackQuery, state: FSMContext):
  user_data = get_user(callback.from_user.id)
  if user_data["balance"] < 100:
    await callback.answer(
        "❌ Недостаточно средств! Нужно минимум 100 коинов.", show_alert=True
    )
    return

  user_data["balance"] -= 100

  builder = InlineKeyboardBuilder()
  builder.button(text="✊ Камень", callback_data="rps_rock")
  builder.button(text="✋ Бумага", callback_data="rps_paper")
  builder.button(text="✌️ Ножницы", callback_data="rps_scissors")
  builder.button(text="❌ Отмена", callback_data="back_home")
  builder.adjust(3, 1)

  await callback.message.edit_text(
      "Дуэль КНБ (Ставка: 100 коинов)\nВыберите свой ход:",
      reply_markup=builder.as_markup(),
  )
  await state.set_state(GameStates.playing_rps)


@dp.callback_query(GameStates.playing_rps, F.data.startswith("rps_"))
async def process_rps(callback: types.CallbackQuery, state: FSMContext):
  user_choice = callback.data.split("_")[1]

  await callback.message.edit_text(
      "Бот анализирует поле боя...\nОжидание результатов (2 сек) 🎲"
  )
  await asyncio.sleep(2)

  bot_choice = random.choice(["rock", "paper", "scissors"])
  user_data = get_user(callback.from_user.id)
  names = {"rock": "✊ Камень", "paper": "✋ Бумага", "scissors": "✌️ Ножницы"}

  if user_choice == bot_choice:
    user_data["balance"] += 100
    res = "Ничья! Ставка возвращена."
  elif (
      (user_choice == "rock" and bot_choice == "scissors")
      or (user_choice == "paper" and bot_choice == "rock")
      or (user_choice == "scissors" and bot_choice == "paper")
  ):
    user_data["balance"] += 200
    res = "Победа! Вы выиграли 200 коинов!"
  else:
    res = "Поражение. Ставка сгорела."

  builder = InlineKeyboardBuilder()
  builder.button(text="🔄 Сыграть еще", callback_data="start_rps")
  builder.button(text="🏠 Главное меню", callback_data="back_home")
  builder.adjust(1)

  text = (
      "ИТОГИ ДУЭЛИ\n\n"
      f"Ваш выбор: {names[user_choice]}\n"
      f"Выбор бота: {names[bot_choice]}\n\n"
      f"{res}\n\n"
      f"Баланс: {user_data['balance']} коинов"
  )
  await callback.message.edit_text(text, reply_markup=builder.as_markup())
  await state.clear()


# ================= КОСТИ =================
@dp.callback_query(F.data == "menu_dice")
async def menu_dice(callback: types.CallbackQuery, state: FSMContext):
  user_data = get_user(callback.from_user.id)
  if user_data["balance"] < 150:
    await callback.answer(
        "❌ Недостаточно коинов! Нужно минимум 150 коинов для ставки.",
        show_alert=True,
    )
    return

  builder = InlineKeyboardBuilder()
  for i in range(1, 7):
    builder.button(text=f"🎲 Число {i}", callback_data=f"dice_bet_{i}")
  builder.button(text="◀️ Назад", callback_data="back_home")
  builder.adjust(3, 3, 1)

  await callback.message.edit_text(
      "Игра «Кости» (Ставка: 150 коинов)\n\n"
      "Угадайте, какое число выпадет на кубике (от 1 до 6).\n"
      "При угадывании вы получаете х3 выигрыш (450 коинов)!\n\n"
      "Выберите число:",
      reply_markup=builder.as_markup(),
  )
  await state.set_state(GameStates.playing_dice_choice)


@dp.callback_query(GameStates.playing_dice_choice, F.data.startswith("dice_bet_"))
async def process_dice(callback: types.CallbackQuery, state: FSMContext):
  user_bet = int(callback.data.split("_")[2])
  user_data = get_user(callback.from_user.id)
  user_data["balance"] -= 150

  await callback.message.edit_text(
      f"Вы поставили на число {user_bet}.\nБросаем игральный кубик... 🎲"
  )
  await asyncio.sleep(1)

  dice_msg = await callback.message.answer_dice(emoji="🎲")
  await asyncio.sleep(3)

  rolled_value = dice_msg.dice.value

  if rolled_value == user_bet:
    win_sum = 450
    user_data["balance"] += win_sum
    result_text = (
        f"Джекпот! Вы угадали число!\nВыпало: {rolled_value}\nВы выиграли"
        f" {win_sum} коинов!"
    )
  else:
    result_text = (
        f"Не угадали.\nВыпало число {rolled_value}, а вы ставили на {user_bet}."
    )

  builder = InlineKeyboardBuilder()
  builder.button(text="🔄 Бросить еще раз", callback_data="menu_dice")
  builder.button(text="🏠 Главное меню", callback_data="back_home")
  builder.adjust(1)

  await callback.message.answer(
      f"{result_text}\n\nБаланс: {user_data['balance']} коинов",
      reply_markup=builder.as_markup(),
  )
  await state.clear()


# ================= БАСКЕТБОЛ =================
@dp.callback_query(F.data == "menu_basket")
async def menu_basket(callback: types.CallbackQuery, state: FSMContext):
  user_data = get_user(callback.from_user.id)
  if user_data["balance"] < 200:
    await callback.answer(
        "❌ Недостаточно средств! Ставка в баскетболе: 200 коинов.",
        show_alert=True,
    )
    return

  user_data["balance"] -= 200
  await callback.message.edit_text(
      "Баскетбольная дуэль (Ставка: 200 коинов)\n\nБросаем мяч в кольцо... 🏟️"
  )
  await asyncio.sleep(1)

  basket_msg = await callback.message.answer_dice(emoji="🏀")
  await asyncio.sleep(3)

  score = basket_msg.dice.value
  is_goal = score in [4, 5]

  if is_goal:
    win_sum = 400
    user_data["balance"] += win_sum
    res_text = "Чистый гол! Мяч в кольце! 🏀\nВы выиграли 400 коинов!"
  else:
    res_text = "Мимо! Мяч отскочил от кольца.\nК сожалению, ставка сгорела."

  builder = InlineKeyboardBuilder()
  builder.button(text="🔄 Бросить снова", callback_data="menu_basket")
  builder.button(text="🏠 Главное меню", callback_data="back_home")
  builder.adjust(1)

  await callback.message.answer(
      f"{res_text}\n\nБаланс: {user_data['balance']} коинов",
      reply_markup=builder.as_markup(),
  )
  await state.clear()


# ================= ВЫВОД ЗВЕЗД =================
@dp.callback_query(F.data == "withdraw")
async def withdraw_stars(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  price = 50000

  if user_data["balance"] < price:
    await callback.answer(
        f"❌ Недостаточно коинов! У вас {user_data['balance']}, а нужно {price}.",
        show_alert=True,
    )
    return

  user_data["balance"] -= price
  user = callback.from_user
  try:
    await bot.send_message(
        ADMIN_ID,
        "НОВАЯ ЗАЯВКА НА ВЫВОД ЗВЕЗД!\n\n"
        f"Пользователь: @{user.username} (ID: {user.id})\n"
        f"Списано коинов: {price}\n"
        "К выдаче: 15 Telegram Stars",
    )
  except Exception:
    pass

  builder = InlineKeyboardBuilder()
  builder.button(text="🏠 На главную", callback_data="back_home")

  await callback.message.edit_text(
      "Заявка успешно оформлена!\n\n"
      "С вашего баланса списано 50 000 коинов.\n"
      "Для получения 15 Telegram Stars (⭐) напишите администратору: "
      "@vouch_01",
      reply_markup=builder.as_markup(),
  )


async def main():
  print("Бот успешно запущен и работает...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
