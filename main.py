import os
import json
import telebot
from flask import Flask, request
from datetime import datetime

# Env variables
TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

# Init
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
processed_updates = set()  # To avoid retry duplicates

# Data store
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Handlers
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Send your winning screenshot! You can send up to 10 per day.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    update_id = message.id
    if update_id in processed_updates:
        return  # Avoid duplicate processing
    processed_updates.add(update_id)

    user_id = str(message.from_user.id)
    today = datetime.now().strftime("%Y-%m-%d")

    data = load_data()

    if user_id not in data:
        data[user_id] = {}

    if today not in data[user_id]:
        data[user_id][today] = 0

    if data[user_id][today] >= 10:
        try:
            bot.reply_to(message, "🚫 Daily limit reached (10 screenshots). Try again tomorrow.")
        except:
            bot.send_message(message.chat.id, "🚫 Daily limit reached (10 screenshots). Try again tomorrow.")
        return

    # Count screenshot
    data[user_id][today] += 1
    save_data(data)

    # Forward photo to admin
    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"📸 From @{message.from_user.username or message.from_user.first_name} (ID: {user_id})"
    )

    try:
        bot.reply_to(message, f"✅ Screenshot received! ({data[user_id][today]}/10 today)")
    except telebot.apihelper.ApiTelegramException as e:
        if "message to be replied not found" in str(e):
            bot.send_message(message.chat.id, f"✅ Screenshot received! ({data[user_id][today]}/10 today)")
        else:
            raise

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    if update.update_id in processed_updates:
        return "Duplicate", 200
    processed_updates.add(update.update_id)

    try:
        bot.process_new_updates([update])
    except Exception as e:
        print("❌ Error:", e)
        return "Error", 500
    return "OK", 200

# Set webhook
@app.route("/", methods=["GET"])
def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}")
    return "✅ Webhook configured", 200

# Run locally or on Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
