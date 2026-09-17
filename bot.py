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
  waiting_result = State()  # Состояние ожидания результата


# Главное меню с красивым дизайном кнопок
def main_menu():
  builder = InlineKeyboardBuilder()
  builder.button(text="👤 Мой профиль", callback_data="profile")
  builder.button(text="🎁 Ежедневный бонус", callback_data="daily_bonus")
  builder.button(text="⚔️ Играть в КНБ (100 коинов)", callback_data="play_menu")
  builder.button(text="🌟 Вывод 15 Звезд (50k)", callback_data="withdraw")
  builder.adjust(1, 1, 1, 1)  расположение кнопками в столбик для красоты
  return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
  await state.clear()
  user = message.from_user
  get_user(user.id)

  text = (
      f"✨ **Привет, {user.first_name}!** ✨\n\n"
      "Добро пожаловать в экономический мини-мир игр!\n"
      "🔹 Зарабатывай коины на дуэлях\n"
      "🔹 Забирай бонусы каждый день\n"
      "🔹 Обменивай коины на реальные Telegram Stars\n\n"
      "👇 Выбери нужный раздел в меню:"
  )
  await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")


@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  text = (
      "📊 **Твой игровой профиль:**\n\n"
      f"💰 Баланс: **{user_data['balance']} коинов**\n"
      "⭐ Курс обмена: 50 000 коинов = 15 Telegram Stars"
  )
  builder = InlineKeyboardBuilder()
  builder.button(text="◀️ Назад в меню", callback_data="back_home")

  await callback.message.edit_text(
      text, reply_markup=builder.as_markup(), parse_mode="Markdown"
  )
  await callback.answer()


@dp.callback_query(F.data == "daily_bonus")
async def daily_bonus(callback: types.CallbackQuery):
  user_data = get_user(callback.from_user.id)
  user_data["balance"] += 200

  await callback.answer(
      "🎉 Успешно! Вы получили бонус +200 коинов!", show_alert=True
  )
  await show_profile(callback)


@dp.callback_query(F.data == "play_menu")
async def play_menu(callback: types.CallbackQuery):
  builder = InlineKeyboardBuilder()
  builder.button(
      text="✊ Камень, ✋ Бумага, ✌️ Ножницы", callback_data="start_rps"
  )
  builder.button(text="◀️ Назад в меню", callback_data="back_home")
  builder.adjust(1)

  await callback.message.edit_text(
      "🎮 **Игровой зал дуэлей:**\n\n"
      "• Ставка за игру: **100 коинов**\n"
      "• При победе ты забираешь: **200 коинов**!\n\n"
      "Сделай шаг навстречу богатству 👇",
      reply_markup=builder.as_markup(),
      parse_mode="Markdown",
  )


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
  builder.adjust(3)

  await callback.message.edit_text(
      "⚔️ **Ставка 100 коинов принята!**\nВыберите свой ход:",
      reply_markup=builder.as_markup(),
      parse_mode="Markdown",
  )
  await state.set_state(GameStates.playing_rps)


# Обработка выбора с ожиданием 2 секунды
@dp.callback_query(GameStates.playing_rps, F.data.startswith("rps_"))
async def process_rps(callback: types.CallbackQuery, state: FSMContext):
  user_choice = callback.data.split("_")[1]

  # Шаг 1: Показываем красивое сообщение об ожидании
  await callback.message.edit_text(
      "⏳ **Бот думает над ходом...**\n*Ожидание результатов (2 сек)* 🎲",
      parse_mode="Markdown",
  )

  # Пауза ровно 2 секунды
  await asyncio.sleep(2)

  bot_choice = random.choice(["rock", "paper", "scissors"])
  user_data = get_user(callback.from_user.id)

  names = {"rock": "✊ Камень", "paper": "✋ Бумага", "scissors": "✌️ Ножницы"}

  if user_choice == bot_choice:
    user_data["balance"] += 100
    res = "🤝 **Ничья!** Ваша ставка возвращена на баланс."
  elif (
      (user_choice == "rock" and bot_choice == "scissors")
      or (user_choice == "paper" and bot_choice == "rock")
      or (user_choice == "scissors" and bot_choice == "paper")
  ):
    user_data["balance"] += 200
    res = "🏆 **Потрясающе! Ты победил и забрал 200 коинов!**"
  else:
    res = "😢 **Увы, в этот раз удача на стороне бота. Ставка сгорела.**"

  builder = InlineKeyboardBuilder()
  builder.button(text="🔄 Сыграть еще раз", callback_data="play_menu")
  builder.button(text="🏠 Главное меню", callback_data="back_home")
  builder.adjust(1)

  text = (
      f"🎯 **ИТОГИ ДУЭЛИ**\n\n"
      f"👤 Твой выбор: {names[user_choice]}\n"
      f"🤖 Выбор бота: {names[bot_choice]}\n\n"
      f"{res}\n\n"
      f"💰 Твой текущий баланс: **{user_data['balance']} коинов**"
  )

  await callback.message.edit_text(
      text, reply_markup=builder.as_markup(), parse_mode="Markdown"
  )
  await state.clear()


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
        "🚨 **НОВАЯ ЗАЯВКА НА ВЫВОД ЗВЕЗД!**\n\n"
        f"👤 Пользователь: @{user.username} (ID: `{user.id}`)\n"
        f"💸 Списано коинов: {price}\n"
        "⭐ К выдаче: **15 Telegram Stars**",
        parse_mode="Markdown",
    )
  except Exception:
    pass

  builder = InlineKeyboardBuilder()
  builder.button(text="🏠 На главную", callback_data="back_home")

  await callback.message.edit_text(
      "✅ **Заявка успешно оформлена!**\n\n"
      "С вашего баланса списано 50 000 коинов.\n"
      "Администратор вскоре проверит запрос и переведет 15 Telegram Stars (⭐).",
      reply_markup=builder.as_markup(),
      parse_mode="Markdown",
  )


@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery, state: FSMContext):
  await state.clear()
  await callback.message.edit_text(
      "✨ **Главное меню экономики:**",
      reply_markup=main_menu(),
      parse_mode="Markdown",
  )
  await callback.answer()


async def main():
  print("Бот с задержкой и дизайном успешно запущен...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
