import os
import json
import datetime
import uuid
import threading
from flask import Flask
import telebot
from telebot.types import Message

app = Flask(__name__)

# Environment variables
BOT_TOKEN = os.environ.get('8498286596:AAH96EBV0tmn9JkOW5y9VQLhg_S8-TusqBc')
ADMIN_ID = int(os.environ.get('6324825537'))
PORT = int(os.environ.get('PORT', 8080))

bot = telebot.TeleBot(BOT_TOKEN)

# Data directory
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
KEYS_FILE = os.path.join(DATA_DIR, 'keys.json')
ACCOUNTS_FILE = os.path.join(DATA_DIR, 'accounts.json')
PENDING_ORDERS_FILE = os.path.join(DATA_DIR, 'pending_orders.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

# Load data functions
def load_data(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return default

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Load all data
users = load_data(USERS_FILE, {})
keys = load_data(KEYS_FILE, [])
accounts = load_data(ACCOUNTS_FILE, [])
pending_orders = load_data(PENDING_ORDERS_FILE, {})
config = load_data(CONFIG_FILE, {'free_service': False, 'last_order_id': 0})

# Helper functions
def is_admin(user_id):
    return user_id == ADMIN_ID

def is_banned(user_id):
    return users.get(str(user_id), {}).get('banned', False)

def is_premium(user_id):
    user_data = users.get(str(user_id), {})
    premium_end = user_data.get('premium_end')
    if premium_end:
        return datetime.datetime.fromisoformat(premium_end) > datetime.datetime.now()
    return False

def get_plan(user_id):
    return 'Premium' if is_premium(user_id) else 'free'

def can_redeem(user_id):
    if is_premium(user_id):
        return True
    if config['free_service']:
        return True
    user_data = users.get(str(user_id), {})
    return not user_data.get('trial_used', False)

def broadcast(message):
    for user_id in list(users.keys()):
        try:
            bot.send_message(int(user_id), message)
        except:
            pass  # Skip if error

def notify_admin(message):
    bot.send_message(ADMIN_ID, message)

# Command handlers
@bot.message_handler(commands=['start'])
def handle_start(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in users:
        users[user_id] = {
            'premium_end': None,
            'trial_used': False,
            'points': 0,
            'banned': False,
            'pending_redeem': False,
            'pending_confirm': False,
            'redeem_messages': []
        }
        save_data(USERS_FILE, users)
    bot.reply_to(message, "Welcome To The Bot ⚡️\nPlease Use this /redeem Command For Get Prime video 🧑‍💻 For Premium use This Command /premium")

@bot.message_handler(commands=['redeem'])
def handle_redeem(message: Message):
    user_id = str(message.from_user.id)
    if is_banned(user_id):
        return
    if user_id not in users:
        users[user_id] = {
            'premium_end': None,
            'trial_used': False,
            'points': 0,
            'banned': False,
            'pending_redeem': False,
            'pending_confirm': False,
            'redeem_messages': []
        }
    if not can_redeem(user_id):
        bot.reply_to(message, "Please Purchase Premium Key For Use 🗝️")
        return
    users[user_id]['pending_redeem'] = True
    users[user_id]['redeem_messages'] = []
    save_data(USERS_FILE, users)
    # No reply sent, silently wait for messages

@bot.message_handler(commands=['premium'])
def handle_premium(message: Message):
    user_id = str(message.from_user.id)
    if is_banned(user_id):
        return
    text = message.text.split()
    if len(text) < 2:
        bot.reply_to(message, "Please use /premium <key>")
        return
    key = text[1]
    for k in keys:
        if k['key'] == key and not k['used']:
            k['used'] = True
            save_data(KEYS_FILE, keys)
            days = k['days']
            end_date = datetime.datetime.now() + datetime.timedelta(days=days)
            users[user_id]['premium_end'] = end_date.isoformat()
            save_data(USERS_FILE, users)
            bot.reply_to(message, "Premium Activated ⚡️")
            notify_admin(f"User {user_id} activated premium with key {key} for {days} days")
            return
    bot.reply_to(message, "Invalid key or already used.")

@bot.message_handler(commands=['genk'])
def handle_genk(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split()
    if len(text) < 2:
        bot.reply_to(message, "Use /genk <days>")
        return
    try:
        days = int(text[1])
    except:
        bot.reply_to(message, "Invalid days")
        return
    key = str(uuid.uuid4())
    keys.append({'key': key, 'days': days, 'used': False})
    save_data(KEYS_FILE, keys)
    bot.reply_to(message, f"Generated key: {key} for {days} days")

@bot.message_handler(commands=['on'])
def handle_on(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    config['free_service'] = True
    save_data(CONFIG_FILE, config)
    broadcast("Free Service On time ⚡️")

@bot.message_handler(commands=['off'])
def handle_off(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    config['free_service'] = False
    save_data(CONFIG_FILE, config)
    broadcast("Free Service Off ♻️")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        bot.reply_to(message, "Use /broadcast <message>")
        return
    broadcast_msg = text[1]
    broadcast(broadcast_msg)

@bot.message_handler(commands=['reply'])
def handle_reply(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split(maxsplit=2)
    if len(text) < 3:
        bot.reply_to(message, "Use /reply <user_id> <message>")
        return
    target_id = text[1]
    reply_msg = text[2]
    try:
        bot.send_message(int(target_id), reply_msg)
        bot.reply_to(message, "Reply sent")
    except:
        bot.reply_to(message, "Failed to send")

@bot.message_handler(commands=['ban'])
def handle_ban(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split()
    if len(text) < 2:
        bot.reply_to(message, "Use /ban <user_id>")
        return
    target_id = text[1]
    if target_id in users:
        users[target_id]['banned'] = True
        save_data(USERS_FILE, users)
        bot.reply_to(message, f"User {target_id} banned")

@bot.message_handler(commands=['unban'])
def handle_unban(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split()
    if len(text) < 2:
        bot.reply_to(message, "Use /unban <user_id>")
        return
    target_id = text[1]
    if target_id in users:
        users[target_id]['banned'] = False
        save_data(USERS_FILE, users)
        bot.reply_to(message, f"User {target_id} unbanned")

@bot.message_handler(commands=['approved', 'failed'])
def handle_approve_fail(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    cmd = message.text.split()[0][1:]  # approved or failed
    text = message.text.split()
    if len(text) < 2:
        bot.reply_to(message, f"Use /{cmd} <order_id>")
        return
    order_id = text[1]
    if order_id not in pending_orders:
        bot.reply_to(message, "Invalid order ID")
        return
    order = pending_orders.pop(order_id)
    save_data(PENDING_ORDERS_FILE, pending_orders)
    target_user_id = order['user_id']
    if cmd == 'approved':
        bot.send_message(int(target_user_id), "Activate Successfully ✅")
        # Broadcast new order done
        user_plan = order['plan']
        user_name = order.get('name', 'Unknown')
        user_username = order.get('username', 'None')
        broadcast_msg = f"""╔═══━─༺༻─━═══╗  
   ♛  New Order Done  ♛  
╚═══━─༺༻─━═══╝  
༺🌸 New Redeem  🌸༻

👤 𝐍𝐚𝐦𝐞 :⫸ {user_name} ⚜️  
✉️ 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞 :⫸ @{user_username} 
🆔 𝐔𝐬𝐞𝐫𝐈𝐃 :⫸ {target_user_id} 
👑 User Plan :⫸ {user_plan} 

⚡ 𝐒𝐞𝐜𝐮𝐫𝐞 Service ⚡"""
        broadcast(broadcast_msg)
    else:
        bot.send_message(int(target_user_id), "Failed For Some Technical issues 🧑‍💻")

@bot.message_handler(commands=['add_accounts'])
def handle_add_accounts(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        bot.reply_to(message, "Use /add_accounts email:xx pass:yy")
        return
    parts = text[1].split()
    if len(parts) < 2:
        bot.reply_to(message, "Invalid format")
        return
    email = parts[0].split(':')[1]
    password = parts[1].split(':')[1]
    accounts.append({'email': email, 'pass': password, 'used_count': 0})
    save_data(ACCOUNTS_FILE, accounts)
    bot.reply_to(message, "Account added")

@bot.message_handler(commands=['add_points'])
def handle_add_points(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    text = message.text.split()
    if len(text) < 3:
        bot.reply_to(message, "Use /add_points <user_id> <points>")
        return
    target_id = text[1]
    try:
        points = int(text[2])
    except:
        bot.reply_to(message, "Invalid points")
        return
    if target_id in users:
        users[target_id]['points'] += points
        save_data(USERS_FILE, users)
        bot.reply_to(message, f"Added {points} points to {target_id}")

@bot.message_handler(commands=['stock'])
def handle_stock(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    available = sum(1 for acc in accounts if acc['used_count'] < 2)
    bot.reply_to(message, f"Available accounts: {available}")

@bot.message_handler(commands=['acc'])
def handle_acc(message: Message):
    user_id = str(message.from_user.id)
    if is_banned(user_id):
        return
    users[user_id]['pending_confirm'] = True
    save_data(USERS_FILE, users)
    bot.reply_to(message, "Please Confirm Purchase 🤳")

@bot.message_handler(commands=['confirm'])
def handle_confirm(message: Message):
    user_id = str(message.from_user.id)
    if is_banned(user_id) or not users.get(user_id, {}).get('pending_confirm', False):
        return
    users[user_id]['pending_confirm'] = False
    save_data(USERS_FILE, users)
    points = users[user_id]['points']
    if points < 5:
        bot.reply_to(message, "Not Enough Points 🪡")
        return
    # Find available account
    for acc in accounts:
        if acc['used_count'] < 2:
            acc['used_count'] += 1
            save_data(ACCOUNTS_FILE, accounts)
            users[user_id]['points'] -= 5
            save_data(USERS_FILE, users)
            bot.reply_to(message, f"""Aᴄᴄᴏᴜɴᴛ Wɪᴛʜᴅʀᴀᴡʟ 🌐

✉ Eᴍᴀɪʟ: {acc['email']}
Password : {acc['pass']} 
🛒 Sᴇʀᴠɪᴄᴇ: Amazon

Thanks For Purchase 😊""")
            return
    bot.reply_to(message, "No accounts available")

# Handle text messages for redeem (expect 2 messages)
@bot.message_handler(func=lambda m: True)
def handle_text(message: Message):
    user_id = str(message.from_user.id)
    if is_banned(user_id) or not users.get(user_id, {}).get('pending_redeem', False):
        return
    users[user_id]['redeem_messages'].append(message.text)
    save_data(USERS_FILE, users)
    
    if len(users[user_id]['redeem_messages']) < 2:
        # Wait for second message
        return
    
    # Got both messages
    users[user_id]['pending_redeem'] = False
    if not can_redeem(user_id):
        bot.reply_to(message, "Please Purchase Premium Key For Use 🗝️")
        users[user_id]['redeem_messages'] = []
        save_data(USERS_FILE, users)
        return
    
    # Count trial if free
    if not is_premium(user_id) and not config['free_service']:
        users[user_id]['trial_used'] = True
    
    # Generate order ID
    config['last_order_id'] += 1
    order_id = str(config['last_order_id'])
    save_data(CONFIG_FILE, config)
    
    # Store order
    messages = users[user_id]['redeem_messages']
    users[user_id]['redeem_messages'] = []
    save_data(USERS_FILE, users)
    
    pending_orders[order_id] = {
        'user_id': user_id,
        'message1': messages[0],
        'message2': messages[1],
        'plan': get_plan(int(user_id)),
        'name': message.from_user.first_name or 'Unknown',
        'username': message.from_user.username or 'None'
    }
    save_data(PENDING_ORDERS_FILE, pending_orders)
    
    # Forward to admin
    notify_admin(f"New redeem from user {user_id} (Order #{order_id}):\nMessage 1: {messages[0]}\nMessage 2: {messages[1]}\nUse /approved {order_id} or /failed {order_id}")
    
    # Send processing to user
    bot.reply_to(message, "Processing 🗝️")

# Flask dummy endpoint for Render
@app.route('/')
def home():
    return "Bot is running"

if __name__ == '__main__':
    # Run bot polling in thread
    threading.Thread(target=bot.polling, daemon=True).start()
    # Run Flask
    app.run(host='0.0.0.0', port=PORT)
