import logging
import json
import os
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration - Using environment variables for security
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Set this in Render environment variables
ADMIN_ID = os.getenv('ADMIN_ID')    # Set this in Render environment variables
ADMIN_USERNAME = "alwayszihan"

# Data storage files - Use /app/data directory for persistence
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

CODES_FILE = os.path.join(DATA_DIR, "codes.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
BANNED_FILE = os.path.join(DATA_DIR, "banned.json")

class GiveawayBot:
    def __init__(self):
        self.codes = self.load_data(CODES_FILE, {})
        self.users = self.load_data(USERS_FILE, {})
        self.banned_users = self.load_data(BANNED_FILE, [])
        
    def load_data(self, filename, default):
        """Load data from JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
        return default
    
    def save_data(self, filename, data):
        """Save data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        return str(user_id) == ADMIN_ID
    
    def is_banned(self, user_id):
        """Check if user is banned"""
        return str(user_id) in self.banned_users
    
    def register_user(self, user):
        """Register user in database"""
        user_id = str(user.id)
        if user_id not in self.users:
            self.users[user_id] = {
                'username': user.username or 'N/A',
                'first_name': user.first_name or 'N/A',
                'last_name': user.last_name or 'N/A',
                'join_date': datetime.now().isoformat(),
                'redeemed_codes': []
            }
            self.save_data(USERS_FILE, self.users)

# Initialize bot instance
bot_instance = GiveawayBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    if bot_instance.is_banned(user.id):
        await update.message.reply_text("❌ You are banned from using this bot.")
        return
    
    bot_instance.register_user(user)
    
    welcome_text = f"""
🎉 **Welcome to ZIHAN GIVEAWAY Bot!** 🇵🇸

Hello {user.first_name}! 👋

This bot allows you to redeem exclusive giveaway codes and win amazing prizes!

**Available Commands:**
• /redeem <code> - Redeem your giveaway code
• /leaderboard - View top winners
• /help - Show help message

🎁 **How to use:**
Simply type `/redeem YOUR_CODE` to claim your prize!

Good luck! 🍀
"""
    
    keyboard = [
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("❓ Help", callback_data='help')],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /redeem command"""
    user = update.effective_user
    
    if bot_instance.is_banned(user.id):
        await update.message.reply_text("❌ You are banned from using this bot.")
        return
    
    bot_instance.register_user(user)
    
    if not context.args:
        await update.message.reply_text(
            "❓ **How to redeem:**\n"
            "Use: `/redeem YOUR_CODE`\n"
            "Example: `/redeem ABC123`",
            parse_mode='Markdown'
        )
        return
    
    code = context.args[0].upper()
    user_id = str(user.id)
    
    # Check if code exists
    if code not in bot_instance.codes:
        await update.message.reply_text("❌ **Invalid code!**\nPlease check your code and try again.", parse_mode='Markdown')
        return
    
    # Check if code is already redeemed
    if bot_instance.codes[code]['redeemed']:
        redeemer_info = bot_instance.codes[code]['redeemer']
        await update.message.reply_text(
            f"❌ **Code already redeemed!**\n"
            f"This code was already used by: {redeemer_info['first_name']} (@{redeemer_info['username']})\n"
            f"Date: {redeemer_info['date']}",
            parse_mode='Markdown'
        )
        return
    
    # Redeem the code
    bot_instance.codes[code]['redeemed'] = True
    bot_instance.codes[code]['redeemer'] = {
        'user_id': user_id,
        'username': user.username or 'N/A',
        'first_name': user.first_name or 'N/A',
        'last_name': user.last_name or 'N/A',
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add to user's redeemed codes
    bot_instance.users[user_id]['redeemed_codes'].append({
        'code': code,
        'prize': bot_instance.codes[code]['prize'],
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Save data
    bot_instance.save_data(CODES_FILE, bot_instance.codes)
    bot_instance.save_data(USERS_FILE, bot_instance.users)
    
    # Send success message to user
    prize = bot_instance.codes[code]['prize']
    await update.message.reply_text(
        f"🎉 **Congratulations!**\n\n"
        f"✅ Code `{code}` redeemed successfully!\n"
        f"🎁 **Prize:** {prize}\n\n"
        f"Contact @{ADMIN_USERNAME} to claim your prize!",
        parse_mode='Markdown'
    )
    
    # Notify admin
    try:
        admin_message = (
            f"🎉 **NEW CODE REDEMPTION**\n\n"
            f"👤 **User:** {user.first_name} {user.last_name or ''}\n"
            f"📱 **Username:** @{user.username or 'N/A'}\n"
            f"🆔 **User ID:** `{user.id}`\n"
            f"🎫 **Code:** `{code}`\n"
            f"🎁 **Prize:** {prize}\n"
            f"📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /info command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    info_text = """
🤖 **ZIHAN GIVEAWAY** 🇵🇸

**Developer:** Latiful Hassan Zihan
**Telegram:** @alwayszihan
**Location:** Bangladesh 🇧🇩
**Language:** Python

**Available Commands:**

👤 **User Commands**
• /start - Shows the main welcome menu
• /redeem <code> - Claim a prize with your code
• /leaderboard - See the top winners
• /help - Shows this help message

👑 **Admin Commands**
• /stats - View bot statistics
• /listcodes - List all codes and prizes
• /addcode <code> - Add a new code
• /addprize <code> <prize> - Set prize for a code
• /delcode <code> - Delete a code
• /gencode <num> <prefix> - Generate codes
• /broadcast <msg> - Send a message to all users
• /ban <user_id> - Ban a user
• /unban <user_id> - Unban a user
• /resetgiveaway - Clear the winner list for a new giveaway
• /stopbot - Stop the bot

Made with ❤️ by Zihan
"""
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    
    if bot_instance.is_banned(user.id):
        await update.message.reply_text("❌ You are banned from using this bot.")
        return
    
    help_text = """
❓ **HELP - How to Use the Bot**

🎁 **For Users:**
• `/start` - Start the bot and see welcome menu
• `/redeem <code>` - Redeem your giveaway code
• `/leaderboard` - View top winners
• `/help` - Show this help message

📝 **How to Redeem:**
1. Get a code from @alwayszihan
2. Type `/redeem YOUR_CODE`
3. If valid, you win the prize!
4. Contact @alwayszihan to claim your prize

🎯 **Example:**
`/redeem ABC123`

💡 **Need a code?** Contact @alwayszihan for giveaways!

Good luck! 🍀
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    if not bot_instance.users:
        await update.message.reply_text("📊 No users have redeemed codes yet!")
        return
    
    # Sort users by number of redeemed codes
    sorted_users = sorted(
        bot_instance.users.items(),
        key=lambda x: len(x[1]['redeemed_codes']),
        reverse=True
    )
    
    leaderboard_text = "🏆 **LEADERBOARD - Top Winners**\n\n"
    
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
        codes_count = len(user_data['redeemed_codes'])
        if codes_count > 0:
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            leaderboard_text += f"{medals[i-1]} **{i}.** {user_data['first_name']} - {codes_count} codes\n"
    
    if leaderboard_text == "🏆 **LEADERBOARD - Top Winners**\n\n":
        leaderboard_text += "No winners yet! Be the first to redeem a code! 🎉"
    
    await update.message.reply_text(leaderboard_text, parse_mode='Markdown')

# Admin Commands

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    total_codes = len(bot_instance.codes)
    redeemed_codes = len([c for c in bot_instance.codes.values() if c['redeemed']])
    total_users = len(bot_instance.users)
    banned_users = len(bot_instance.banned_users)
    
    stats_text = f"""
📊 **BOT STATISTICS**

🎫 **Codes:**
• Total: {total_codes}
• Redeemed: {redeemed_codes}
• Available: {total_codes - redeemed_codes}

👥 **Users:**
• Total Users: {total_users}
• Banned Users: {banned_users}
• Active Users: {total_users - banned_users}

📈 **Success Rate:** {(redeemed_codes/total_codes*100):.1f}% if total_codes > 0 else 0%
"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def listcodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listcodes command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not bot_instance.codes:
        await update.message.reply_text("📋 No codes available yet!")
        return
    
    codes_text = "📋 **ALL CODES**\n\n"
    
    for code, data in bot_instance.codes.items():
        status = "✅ Redeemed" if data['redeemed'] else "⏳ Available"
        codes_text += f"🎫 `{code}` - {data['prize']} ({status})\n"
        if data['redeemed']:
            codes_text += f"   👤 By: {data['redeemer']['first_name']}\n"
        codes_text += "\n"
    
    await update.message.reply_text(codes_text, parse_mode='Markdown')

async def addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcode command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/addcode CODE`\nExample: `/addcode ABC123`", parse_mode='Markdown')
        return
    
    code = context.args[0].upper()
    
    if code in bot_instance.codes:
        await update.message.reply_text(f"❌ Code `{code}` already exists!", parse_mode='Markdown')
        return
    
    bot_instance.codes[code] = {
        'prize': 'No prize set',
        'redeemed': False,
        'redeemer': None,
        'created_date': datetime.now().isoformat()
    }
    
    bot_instance.save_data(CODES_FILE, bot_instance.codes)
    
    await update.message.reply_text(f"✅ Code `{code}` added successfully!\nUse `/addprize {code} PRIZE_NAME` to set a prize.", parse_mode='Markdown')

async def addprize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addprize command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/addprize CODE PRIZE_NAME`\nExample: `/addprize ABC123 iPhone 15`", parse_mode='Markdown')
        return
    
    code = context.args[0].upper()
    prize = ' '.join(context.args[1:])
    
    if code not in bot_instance.codes:
        await update.message.reply_text(f"❌ Code `{code}` doesn't exist! Add it first with `/addcode {code}`", parse_mode='Markdown')
        return
    
    bot_instance.codes[code]['prize'] = prize
    bot_instance.save_data(CODES_FILE, bot_instance.codes)
    
    await update.message.reply_text(f"✅ Prize set for code `{code}`: {prize}", parse_mode='Markdown')

async def delcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delcode command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/delcode CODE`\nExample: `/delcode ABC123`", parse_mode='Markdown')
        return
    
    code = context.args[0].upper()
    
    if code not in bot_instance.codes:
        await update.message.reply_text(f"❌ Code `{code}` doesn't exist!", parse_mode='Markdown')
        return
    
    del bot_instance.codes[code]
    bot_instance.save_data(CODES_FILE, bot_instance.codes)
    
    await update.message.reply_text(f"✅ Code `{code}` deleted successfully!", parse_mode='Markdown')

async def gencode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /gencode command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/gencode NUMBER PREFIX`\nExample: `/gencode 5 GIVEAWAY`", parse_mode='Markdown')
        return
    
    try:
        num = int(context.args[0])
        prefix = context.args[1].upper()
        
        if num > 50:
            await update.message.reply_text("❌ Maximum 50 codes can be generated at once!")
            return
        
        generated_codes = []
        
        for _ in range(num):
            while True:
                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                code = f"{prefix}{suffix}"
                if code not in bot_instance.codes:
                    break
            
            bot_instance.codes[code] = {
                'prize': 'No prize set',
                'redeemed': False,
                'redeemer': None,
                'created_date': datetime.now().isoformat()
            }
            generated_codes.append(code)
        
        bot_instance.save_data(CODES_FILE, bot_instance.codes)
        
        codes_text = f"✅ Generated {num} codes:\n\n"
        for code in generated_codes:
            codes_text += f"`{code}`\n"
        
        await update.message.reply_text(codes_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Number must be a valid integer!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast MESSAGE`\nExample: `/broadcast New giveaway is live!`", parse_mode='Markdown')
        return
    
    message = ' '.join(context.args)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text("📢 Broadcasting message to all users...")
    
    for user_id in bot_instance.users.keys():
        if user_id not in bot_instance.banned_users:
            try:
                await context.bot.send_message(chat_id=int(user_id), text=f"📢 **ANNOUNCEMENT**\n\n{message}", parse_mode='Markdown')
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                failed_count += 1
    
    await update.message.reply_text(f"✅ Broadcast complete!\n📤 Sent: {sent_count}\n❌ Failed: {failed_count}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ban command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/ban USER_ID`\nExample: `/ban 123456789`", parse_mode='Markdown')
        return
    
    try:
        user_id = str(context.args[0])
        
        if user_id == ADMIN_ID:
            await update.message.reply_text("❌ You can't ban yourself!")
            return
        
        if user_id not in bot_instance.banned_users:
            bot_instance.banned_users.append(user_id)
            bot_instance.save_data(BANNED_FILE, bot_instance.banned_users)
            await update.message.reply_text(f"✅ User {user_id} has been banned!")
        else:
            await update.message.reply_text(f"⚠️ User {user_id} is already banned!")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unban command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/unban USER_ID`\nExample: `/unban 123456789`", parse_mode='Markdown')
        return
    
    try:
        user_id = str(context.args[0])
        
        if user_id in bot_instance.banned_users:
            bot_instance.banned_users.remove(user_id)
            bot_instance.save_data(BANNED_FILE, bot_instance.banned_users)
            await update.message.reply_text(f"✅ User {user_id} has been unbanned!")
        else:
            await update.message.reply_text(f"⚠️ User {user_id} is not banned!")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def resetgiveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resetgiveaway command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    # Reset all codes to unredeemed
    for code in bot_instance.codes:
        bot_instance.codes[code]['redeemed'] = False
        bot_instance.codes[code]['redeemer'] = None
    
    # Clear user redemption history
    for user_id in bot_instance.users:
        bot_instance.users[user_id]['redeemed_codes'] = []
    
    bot_instance.save_data(CODES_FILE, bot_instance.codes)
    bot_instance.save_data(USERS_FILE, bot_instance.users)
    
    await update.message.reply_text("✅ Giveaway has been reset! All codes are now available again.")

async def stopbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopbot command (Admin only)"""
    if not bot_instance.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    await update.message.reply_text("🛑 Bot is shutting down...")
    
    # Send shutdown notification to admin
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text="🛑 Bot has been stopped by admin command.")
    except:
        pass
    
    # Stop the application
    application = context.application
    await application.stop()

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands"""
    await update.message.reply_text(
        "❓ Unknown command! Use /help to see available commands.",
        parse_mode='Markdown'
    )

def main():
    """Main function to run the bot"""
    # Check if environment variables are set
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    
    if not ADMIN_ID:
        logger.error("ADMIN_ID environment variable is not set!")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    
    # Admin commands
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("listcodes", listcodes))
    application.add_handler(CommandHandler("addcode", addcode))
    application.add_handler(CommandHandler("addprize", addprize))
    application.add_handler(CommandHandler("delcode", delcode))
    application.add_handler(CommandHandler("gencode", gencode))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("resetgiveaway", resetgiveaway))
    application.add_handler(CommandHandler("stopbot", stopbot))
    
    # Handle unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Run the bot
    logger.info("🚀 ZIHAN GIVEAWAY Bot is starting...")
    logger.info(f"👑 Admin: @{ADMIN_USERNAME}")
    logger.info("🔄 Bot is running...")
    
    application.run_polling()

if __name__ == '__main__':
    main()