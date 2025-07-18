import os
import telebot
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]  # e.g. https://your-app.onrender.com/<BOT_TOKEN>

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
received_users = set()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Send your screenshot!")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    if user_id in received_users:
        bot.reply_to(message, "⚠️ Duplicate screenshot.")
        return
    received_users.add(user_id)
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                   caption=f"From @{message.from_user.username or message.from_user.first_name} (ID: {user_id})")
    bot.reply_to(message, "✅ Screenshot received!")

# Endpoint Telegram uses to POST updates
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "OK", 200

# Setup webhook via GET on root
@app.route("/", methods=["GET"])
def setup():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return "Webhook configured", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
