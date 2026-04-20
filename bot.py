python
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8683839475:AAFkhwjDa4RznPxJ5LGkLImXNwSRbYLYNFy"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Сәлем! Мен 24/7 жұмыс істейтін ботпын!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Командалар:\n/start - бастау\n/help - көмек")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    print("🤖 Бот жұмыс істейді...")
    app.run_polling()

if __name__ == "__main__":
    main()
