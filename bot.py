import json
import os
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8683839475:AAFkhwjDa4RznPxJ5LGkLImXNwSRbYLYNFy"

# Файлдар
USER_DATA_FILE = "user_data.json"
FOODS_FILE = "foods.json"

# Тағамдар базасы (калория 100 граммға)
DEFAULT_FOODS = {
    "алма": 52,
    "банан": 89,
    "нан": 265,
    "күріш": 130,
    "тауық еті": 165,
    "балық": 206,
    "жұмыртқа": 155,
    "сүт": 42,
    "йогурт": 61,
    "картоп": 77,
    "макарон": 131,
    "шұжық": 300,
    "печенье": 500,
    "шоколад": 546,
    "кока-кола": 42,
}

def load_foods():
    if os.path.exists(FOODS_FILE):
        with open(FOODS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_FOODS.copy()

def save_foods(foods):
    with open(FOODS_FILE, 'w', encoding='utf-8') as f:
        json.dump(foods, f, ensure_ascii=False, indent=2)

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Команда: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {
            "daily_calories": 2000,  # күнделікті норма
            "history": {},
            "today_calories": 0
        }
        save_user_data(user_data)
    
    keyboard = [
        [InlineKeyboardButton("➕ Тағам қосу", callback_data="add_food")],
        [InlineKeyboardButton("📊 Бүгінгі калория", callback_data="show_today")],
        [InlineKeyboardButton("📈 Апталық статистика", callback_data="show_week")],
        [InlineKeyboardButton("⚙️ Күнделікті норманы өзгерту", callback_data="set_norm")],
        [InlineKeyboardButton("📋 Тағамдар тізімі", callback_data="food_list")],
        [InlineKeyboardButton("➕ Жаңа тағам қосу", callback_data="new_food")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🍏 **Калория есептегіш бот**\n\n"
        "Мен сізге күнделікті калорияны санауға көмектесемін.\n\n"
        f"⚡ Сіздің күнделікті нормаңыз: **{user_data[user_id]['daily_calories']} ккал**\n\n"
        "Төмендегі батырмаларды пайдаланыңыз:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Тағам қосу
async def add_food_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    foods = load_foods()
    keyboard = []
    row = []
    
    for i, (name, calories) in enumerate(foods.items()):
        row.append(InlineKeyboardButton(name.capitalize(), callback_data=f"food_{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Артқа", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🍽️ **Қандай тағам қосқыңыз келеді?**\n\n"
        "Тағамды таңдаңыз:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    context.user_data['waiting_for_food'] = False

# Таңдалған тағамды өңдеу
async def handle_food_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    food_name = query.data.replace("food_", "")
    context.user_data['selected_food'] = food_name
    context.user_data['waiting_for_grams'] = True
    
    foods = load_foods()
    calories_per_100g = foods.get(food_name, 100)
    
    keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="add_food")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🍽️ **{food_name.capitalize()}**\n\n"
        f"🔥 100 граммда: **{calories_per_100g} ккал**\n\n"
        f"Қанша грамм жедіңіз? Санды жазыңыз:\n"
        f"(мысалы: 150)",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Грамм мөлшерін өңдеу
async def handle_grams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_grams'):
        return
    
    try:
        grams = float(update.message.text.strip())
        if grams <= 0:
            await update.message.reply_text("❌ Мөлшер 0-ден үлкен болуы керек!")
            return
        
        food_name = context.user_data['selected_food']
        foods = load_foods()
        calories_per_100g = foods.get(food_name, 100)
        
        # Калория есептеу
        calories = (grams / 100) * calories_per_100g
        
        # Пайдаланушының дерегін жаңарту
        user_id = str(update.effective_user.id)
        user_data = load_user_data()
        today = str(date.today())
        
        if user_id not in user_data:
            user_data[user_id] = {"daily_calories": 2000, "history": {}, "today_calories": 0}
        
        if today not in user_data[user_id]['history']:
            user_data[user_id]['history'][today] = []
        
        user_data[user_id]['history'][today].append({
            "food": food_name,
            "grams": grams,
            "calories": round(calories, 1),
            "time": datetime.now().strftime("%H:%M")
        })
        
        # Бүгінгі калорияны қайта есептеу
        total = sum(item['calories'] for item in user_data[user_id]['history'][today])
        user_data[user_id]['today_calories'] = round(total, 1)
        save_user_data(user_data)
        
        # Келесі күніңіз
        daily_norm = user_data[user_id]['daily_calories']
        remaining = daily_norm - total
        status = "✅ Қалыпты" if remaining > 0 else "⚠️ Нормадан астыңыз"
        
        await update.message.reply_text(
            f"✅ **Қосылды!**\n\n"
            f"🍽️ {food_name.capitalize()}: {grams} г = **{round(calories, 1)} ккал**\n"
            f"📊 Бүгін жинаған: **{round(total, 1)}** / {daily_norm} ккал\n"
            f"💪 Қалған: **{round(remaining, 1)}** ккал\n"
            f"📌 {status}",
            parse_mode="Markdown"
        )
        
        context.user_data['waiting_for_grams'] = False
        context.user_data['selected_food'] = None
        
        # Мәзірге қайтару
        await show_menu(update, context)
        
    except ValueError:
        await update.message.reply_text("❌ Санды дұрыс енгізіңіз (мысалы: 150)")

# Бүгінгі статистика
async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    today = str(date.today())
    
    if user_id not in user_data:
        await query.edit_message_text("Дерек жоқ. /start басыңыз")
        return
    
    daily_norm = user_data[user_id]['daily_calories']
    total = user_data[user_id].get('today_calories', 0)
    remaining = daily_norm - total
    
    history = user_data[user_id]['history'].get(today, [])
    
    if not history:
        text = f"📊 **Бүгін ештеңе жемедіңіз**\n\n🔥 Калория: 0 / {daily_norm} ккал"
    else:
        food_list = "\n".join([f"• {item['food']} - {item['grams']}г ({item['calories']} ккал)" for item in history])
        text = f"📊 **Бүгінгі статистика**\n\n{food_list}\n\n🔥 **Жалпы: {round(total, 1)} / {daily_norm} ккал**\n💪 Қалған: {round(remaining, 1)} ккал"
    
    keyboard = [[InlineKeyboardButton("🔙 Мәзірге", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Апталық статистика
async def show_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text("Дерек жоқ. /start басыңыз")
        return
    
    text = "📈 **Соңғы 7 күн**\n\n"
    for i in range(7):
        day = date.fromordinal(date.today().toordinal() - i)
        day_str = str(day)
        calories = 0
        if day_str in user_data[user_id]['history']:
            calories = sum(item['calories'] for item in user_data[user_id]['history'][day_str])
        text += f"• {day.strftime('%d.%m')}: {round(calories, 1)} ккал\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Мәзірге", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Күнделікті норманы өзгерту
async def set_norm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for_norm'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ **Күнделікті калория нормасын өзгерту**\n\n"
        "Жаңа норманы санмен жазыңыз (мысалы: 2000):",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_set_norm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_norm'):
        return
    
    try:
        new_norm = float(update.message.text.strip())
        if new_norm <= 0:
            await update.message.reply_text("❌ Норма 0-ден үлкен болуы керек!")
            return
        
        user_id = str(update.effective_user.id)
        user_data = load_user_data()
        
        if user_id not in user_data:
            user_data[user_id] = {"daily_calories": 2000, "history": {}, "today_calories": 0}
        
        user_data[user_id]['daily_calories'] = new_norm
        save_user_data(user_data)
        
        await update.message.reply_text(f"✅ Күнделікті норма **{new_norm} ккал** болып өзгертілді!")
        
        context.user_data['waiting_for_norm'] = False
        await show_menu(update, context)
        
    except ValueError:
        await update.message.reply_text("❌ Санды дұрыс енгізіңіз!")

# Тағамдар тізімі
async def show_food_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    foods = load_foods()
    text = "📋 **Тағамдар тізімі (100г калория)**\n\n"
    for name, calories in foods.items():
        text += f"• {name.capitalize()}: {calories} ккал\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Мәзірге", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Жаңа тағам қосу
async def new_food_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for_new_food_name'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Артқа", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➕ **Жаңа тағам қосу**\n\n"
        "Тағамның атын жазыңыз:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_new_food_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_new_food_name'):
        return
    
    food_name = update.message.text.strip().lower()
    context.user_data['new_food_name'] = food_name
    context.user_data['waiting_for_new_food_name'] = False
    context.user_data['waiting_for_new_food_calories'] = True
    
    await update.message.reply_text(
        f"'{food_name.capitalize()}' үшін 100 граммдағы калория мөлшерін жазыңыз:"
    )

async def handle_new_food_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_new_food_calories'):
        return
    
    try:
        calories = float(update.message.text.strip())
        food_name = context.user_data['new_food_name']
        
        foods = load_foods()
        foods[food_name] = calories
        save_foods(foods)
        
        await update.message.reply_text(f"✅ '{food_name.capitalize()}' қосылды! ({calories} ккал/100г)")
        
        context.user_data['waiting_for_new_food_calories'] = False
        context.user_data['new_food_name'] = None
        await show_menu(update, context)
        
    except ValueError:
        await update.message.reply_text("❌ Калорияны санмен жазыңыз!")

# Мәзірге қайту
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_menu(update, context)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {"daily_calories": 2000, "history": {}, "today_calories": 0}
        save_user_data(user_data)
    
    keyboard = [
        [InlineKeyboardButton("➕ Тағам қосу", callback_data="add_food")],
        [InlineKeyboardButton("📊 Бүгінгі калория", callback_data="show_today")],
        [InlineKeyboardButton("📈 Апталық статистика", callback_data="show_week")],
        [InlineKeyboardButton("⚙️ Күнделікті норманы өзгерту", callback_data="set_norm")],
        [InlineKeyboardButton("📋 Тағамдар тізімі", callback_data="food_list")],
        [InlineKeyboardButton("➕ Жаңа тағам қосу", callback_data="new_food")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(
            f"🍏 **Калория есептегіш**\n\n"
            f"⚡ Сіздің күнделікті нормаңыз: **{user_data[user_id]['daily_calories']} ккал**\n"
            f"📊 Бүгін: **{user_data[user_id]['today_calories']}** / {user_data[user_id]['daily_calories']} ккал\n\n"
            f"Төмендегі батырмаларды пайдаланыңыз:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🍏 **Калория есептегіш**\n\n"
            f"⚡ Сіздің күнделікті нормаңыз: **{user_data[user_id]['daily_calories']} ккал**\n"
            f"📊 Бүгін: **{user_data[user_id]['today_calories']}** / {user_data[user_id]['daily_calories']} ккал\n\n"
            f"Төмендегі батырмаларды пайдаланыңыз:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# Бас функция
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Командалар
    app.add_handler(CommandHandler("start", start))
    
    # Callback обработчиктері
    app.add_handler(CallbackQueryHandler(add_food_start, pattern="add_food"))
    app.add_handler(CallbackQueryHandler(show_today, pattern="show_today"))
    app.add_handler(CallbackQueryHandler(show_week, pattern="show_week"))
    app.add_handler(CallbackQueryHandler(set_norm, pattern="set_norm"))
    app.add_handler(CallbackQueryHandler(show_food_list, pattern="food_list"))
    app.add_handler(CallbackQueryHandler(new_food_start, pattern="new_food"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
    app.add_handler(CallbackQueryHandler(handle_food_selection, pattern="^food_"))
    
    # Хабарлама обработчиктері
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_grams))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_norm))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_food_name))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_food_calories))
    
    print("🤖 Калория боты жұмыс істейді...")
    app.run_polling()

if __name__ == "__main__":
    main()
