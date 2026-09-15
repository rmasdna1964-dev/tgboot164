import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import LabeledPrice

# Токен первого бота (Магазин): @vouch_01_rep_bot
SHOP_TOKEN = "8838093580:AAEDZArbQx7N5B-acHHp9JIkSCuf6nToQFI"

# Токен второго бота (Админ-бот), который присылает тебе уведомления
ADMIN_BOT_TOKEN = "8623258820:AAEInCHPfQXtgMcW6i5Ftt07ewy9JXFlxaE"

# Твой реальный Telegram ID
MY_TELEGRAM_ID = 8706958823

bot_shop = Bot(token=SHOP_TOKEN)
bot_admin_sender = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()

ITEM_TITLE = "Виртуальный номер +65"
ITEM_DESCRIPTION = "Покупка номера +65 (Сингапур). В наличии 1 шт."
PRICE_IN_STARS = 1  # Цена ровно 1 звезда

stock_available = True  # В наличии 1 шт. (+65)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
  keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
      types.InlineKeyboardButton(
          text=f"Купить номер +65 🇸🇬 ({PRICE_IN_STARS} ⭐)",
          callback_data="buy_number"),
  ]])
  await message.answer(
      "👋 Добро пожаловать в магазин номеров!\n\n"
      "📦 **Товар в наличии:**\n"
      "• Номер: `+65` (Сингапур)\n"
      f"• Цена: **{PRICE_IN_STARS} ⭐**\n\n"
      "Нажми кнопку ниже для покупки:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


@dp.callback_query(F.data == "buy_number")
async def process_buy(callback: types.CallbackQuery):
  global stock_available

  if not stock_available:
    await callback.answer(
        "❌ Этот номер уже купили! Больше нет в наличии.", show_alert=True
    )
    return

  # Создаем счет на оплату в 1 звезду (валюта 'XTR')
  prices = [LabeledPrice(label="Номер +65", amount=PRICE_IN_STARS)]

  await callback.message.answer_invoice(
      title=ITEM_TITLE,
      description=ITEM_DESCRIPTION,
      prices=prices,
      provider_token="",  # Для Telegram Stars всегда пустая строка
      payload="number_65_payload",
      currency="XTR",
  )
  await callback.answer()


@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
  global stock_available
  if not stock_available:
    await pre_checkout_query.answer(
        ok=False, error_message="К сожалению, товар только что закончился!"
    )
    return
  await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
  global stock_available

  if not stock_available:
    await message.answer("Ошибка: товар уже был продан.")
    return

  # Снимаем товар с наличия
  stock_available = False
  secret_number = "+65 1234 5678 (данные для входа / код)"

  # 1. Выдаем номер покупателю
  await message.answer(
      "✅ **Оплата прошла успешно! Спасибо за покупку!** 🎉\n\n"
      "Вот твой товар (номер +65):\n"
      f"🔒 `{secret_number}`",
      parse_mode="Markdown",
  )

  # 2. Собираем информацию о покупателе
  buyer = message.from_user
  buyer_name = buyer.full_name
  buyer_username = f"@{buyer.username}" if buyer.username else "нет юзернейма"
  buyer_id = buyer.id

  # 3. Формируем отчет для тебя
  notification_text = (
      "🚨 **Купили номер за 1 звезду!**\n\n"
      f"👤 **Покупатель:** {buyer_name} ({buyer_username})\n"
      f"🆔 **ID:** `{buyer_id}`\n"
      "📦 **Товар:** Номер +65\n"
      f"⭐ **Сумма:** {PRICE_IN_STARS} Star"
  )

  # Кнопка для быстрой связи с покупателем
  contact_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
      types.InlineKeyboardButton(
          text="💬 Написать покупателю", url=f"tg://user?id={buyer_id}"
      )
  ]])

  # 4. Второй бот шлет тебе уведомление в личку
  try:
    await bot_admin_sender.send_message(
        chat_id=MY_TELEGRAM_ID,
        text=notification_text,
        reply_markup=contact_keyboard,
        parse_mode="Markdown",
    )
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление админу: {e}")


async def main():
  logging.basicConfig(level=logging.INFO)
  print("Бот-магазин запущен...")
  await dp.start_polling(bot_shop)


if __name__ == "__main__":
  asyncio.run(main())
