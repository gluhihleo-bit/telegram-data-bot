import logging
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
from flask import Flask
import threading

# Flask для поддержания работы
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния разговора
NAME, PHONE, ADDRESS = range(3)

# Файл для хранения данных
EXCEL_FILE = "client_data.xlsx"

# Клавиатура с кнопкой отправки контакта
def get_contact_keyboard():
    keyboard = [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_main_keyboard():
    keyboard = [
        ["📝 Начать сбор данных"],
        ["📊 Получить Excel отчет"],
        ["📋 Последние 5 записей"],
        ["🗑 Очистить все данные"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Создание Excel файла если не существует
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=['ID', 'Дата', 'Имя', 'Телефон', 'Адрес'])
        df.to_excel(EXCEL_FILE, index=False)
        logger.info("Создан новый Excel файл")

# Сохранение данных в Excel
def save_to_excel(name, phone, address):
    try:
        df = pd.read_excel(EXCEL_FILE)
    except:
        df = pd.DataFrame(columns=['ID', 'Дата', 'Имя', 'Телефон', 'Адрес'])
    
    new_id = len(df) + 1
    new_row = {
        'ID': new_id,
        'Дата': datetime.now().strftime("%d.%m.%Y %H:%M"),
        'Имя': name,
        'Телефон': phone,
        'Адрес': address
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)
    logger.info(f"Данные сохранены: {name}, {phone}")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Здравствуйте! Я бот для сбора данных.\n\n"
        "Я помогу собрать:\n"
        "📱 Номера телефонов\n"
        "📍 Адреса клиентов\n"
        "📊 Автоматически создам Excel отчет\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

# Начало сбора данных
async def start_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ваше имя:")
    return NAME

# Получение имени
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "Отправьте ваш номер телефона:",
        reply_markup=get_contact_keyboard()
    )
    return PHONE

# Получение телефона
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    
    context.user_data['phone'] = phone
    await update.message.reply_text(
        "Введите ваш адрес (город, улица, дом, квартира):",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return ADDRESS

# Получение адреса и сохранение
async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    
    # Сохраняем в Excel
    save_to_excel(
        context.user_data['name'],
        context.user_data['phone'],
        context.user_data['address']
    )
    
    await update.message.reply_text(
        f"✅ Данные успешно сохранены!\n\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"📱 Телефон: {context.user_data['phone']}\n"
        f"📍 Адрес: {context.user_data['address']}",
        reply_markup=get_main_keyboard()
    )
    
    return ConversationHandler.END

# Отправка Excel файла
async def send_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        if len(df) == 0:
            await update.message.reply_text("📋 База данных пуста")
            return
        
        await update.message.reply_document(
            document=open(EXCEL_FILE, 'rb'),
            filename=f"client_data_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx",
            caption=f"📊 Отчет содержит {len(df)} записей"
        )
    else:
        await update.message.reply_text("❌ Файл с данными не найден")

# Показать последние 5 записей
async def show_last_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("📋 База данных пуста")
        return
    
    df = pd.read_excel(EXCEL_FILE)
    if len(df) == 0:
        await update.message.reply_text("📋 База данных пуста")
        return
    
    last_records = df.tail(5)
    message = "📋 Последние 5 записей:\n\n"
    
    for _, row in last_records.iterrows():
        message += f"ID: {row['ID']}\n"
        message += f"📅 {row['Дата']}\n"
        message += f"👤 {row['Имя']}\n"
        message += f"📱 {row['Телефон']}\n"
        message += f"📍 {row['Адрес']}\n"
        message += "─" * 30 + "\n"
    
    await update.message.reply_text(message)

# Очистка данных
async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["✅ Да, удалить все", "❌ Нет, отмена"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "⚠️ Вы уверены, что хотите удалить все данные?\nЭто действие нельзя отменить!",
        reply_markup=reply_markup
    )
    return "CLEAR_CONFIRM"

async def confirm_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ Да, удалить все":
        df = pd.DataFrame(columns=['ID', 'Дата', 'Имя', 'Телефон', 'Адрес'])
        df.to_excel(EXCEL_FILE, index=False)
        await update.message.reply_text(
            "🗑 Все данные удалены",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Операция отменена",
            reply_markup=get_main_keyboard()
        )
    return ConversationHandler.END

# Отмена операции
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Операция отменена",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# Обработка текстовых команд
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "📝 Начать сбор данных":
        return await start_collection(update, context)
    elif text == "📊 Получить Excel отчет":
        await send_excel(update, context)
    elif text == "📋 Последние 5 записей":
        await show_last_records(update, context)
    elif text == "🗑 Очистить все данные":
        return await clear_data(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации",
            reply_markup=get_main_keyboard()
        )

def run_bot():
    # Токен из переменных окружения
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        logger.error("Токен не найден! Установите переменную BOT_TOKEN")
        return
    
    # Инициализация Excel файла
    init_excel()
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Conversation handler для сбора данных
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^📝 Начать сбор данных$'), start_collection),
            MessageHandler(filters.Regex('^🗑 Очистить все данные$'), clear_data)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            "CLEAR_CONFIRM": [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_clear)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Добавление обработчиков
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))))
    flask_thread.start()
    
    # Запуск бота
    run_bot()