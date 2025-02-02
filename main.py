import os
import re
import smtplib
import dns.resolver
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Данные для SMTP из переменных окружения
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.yandex.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER", "example@yandex.ru")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_password")

# Токен Telegram-бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# Словарь для хранения состояний пользователей
user_data = {}

# Проверка синтаксиса email
def is_valid_email_format(email):
    pattern = r"^[\w\.-]+@[a-zA-Z\d\.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

# Проверка домена email через MX-записи
def is_valid_email_domain(email):
    try:
        domain = email.split('@')[1]
        mx_records = dns.resolver.resolve(domain, 'MX')
        if mx_records:
            return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False
    return False

# Проверка email
def is_valid_email(email):
    if not is_valid_email_format(email):
        return False
    if not is_valid_email_domain(email):
        return False
    return True

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"email": None, "message": None}
    await update.message.reply_text("Привет! Укажите email, на который хотите отправить сообщение:")

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("Начни с команды /start.")
        return

    if not user_data[user_id]["email"]:
        # Проверка email
        email = update.message.text
        if is_valid_email(email):
            user_data[user_id]["email"] = email
            await update.message.reply_text("Отлично! Теперь напишите текст сообщения:")
        else:
            await update.message.reply_text("Пожалуйста, введите корректный и существующий email.")
    elif not user_data[user_id]["message"]:
        # Сохранение сообщения
        user_data[user_id]["message"] = update.message.text
        email = user_data[user_id]["email"]
        message = user_data[user_id]["message"]

        try:
            # Отправка письма
            send_email(email, message)
            await update.message.reply_text(f"Сообщение успешно отправлено на {email}!")
        except Exception as e:
            await update.message.reply_text(f"Произошла ошибка при отправке письма: {e}")

        # Сброс состояния
        user_data.pop(user_id, None)

# Функция отправки email через SMTP
def send_email(recipient_email, message_text):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = recipient_email
    msg["Subject"] = "Сообщение от Telegram-бота"

    msg.attach(MIMEText(message_text, "plain"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, recipient_email, msg.as_string())

# Основной код приложения
if __name__ == "__main__":
    # Проверка наличия токена
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token":
        raise ValueError("Токен бота не задан. Установите его через переменные окружения.")

    # Создание и запуск приложения
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    app.run_polling()
