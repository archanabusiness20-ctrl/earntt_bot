import logging
import re
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ══════════════════════════════════════════════
#   CONFIG — Yahan apni keys daalein
# ══════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = "7565465167:AAGFJ4WOh_URYv7ZWvdmwc6NoW_fiuaa8BY"   # @BotFather se milega
EARNKARO_API_KEY   = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NzM5NjBmZWE5NjhhMmUyZDQ3MzBlNGQiLCJlYXJua2FybyI6IjM5ODA4MTUiLCJpYXQiOjE3ODIxMjQwNDl9.HECX7u10iMy83cqzAAEI9hWVgGmBgrI3Y80BhvJkbBw"      # EarnKaro dashboard se
TARGET_GROUP_ID    = None  # Optional: "-1001234567890" (group mein auto-post ke liye)

# ══════════════════════════════════════════════
#   LOGGING SETUP
# ══════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#   SUPPORTED PLATFORMS
# ══════════════════════════════════════════════
SUPPORTED_DOMAINS = [
    "amazon.in", "amzn.in", "amzn.to",
    "flipkart.com", "fkrt.it",
    "myntra.com",
    "ajio.com",
    "nykaa.com",
    "meesho.com",
    "snapdeal.com",
    "tatacliq.com",
]

def detect_platform(url: str) -> str:
    if "amazon" in url or "amzn" in url:
        return "🛒 Amazon"
    elif "flipkart" in url or "fkrt" in url:
        return "🏪 Flipkart"
    elif "myntra" in url:
        return "👗 Myntra"
    elif "ajio" in url:
        return "👔 AJIO"
    elif "nykaa" in url:
        return "💄 Nykaa"
    elif "meesho" in url:
        return "🛍️ Meesho"
    else:
        return "🔗 Store"

def extract_urls(text: str) -> list[str]:
    """Message se saare URLs nikaalein"""
    pattern = r'https?://[^\s]+'
    return re.findall(pattern, text)

def is_supported(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

# ══════════════════════════════════════════════
#   EARNKARO API CALL (FIXED)
# ══════════════════════════════════════════════
def convert_to_affiliate(original_url: str) -> dict:
    """
    EarnKaro API se affiliate link banao.
    API: https://ekaro-api.affiliaters.in/api/converter/public
    """
    try:
        response = requests.post(
            "https://ekaro-api.affiliaters.in/api/converter/public",
            headers={
                "Authorization": f"Bearer {EARNKARO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "deal": original_url,
                "convert_option": "convert_only"
            },
            timeout=10,
        )
        data = response.json()

        if response.ok and data.get("success"):
            aff_link = data.get("data")  # Direct string aata hai
            return {
                "success": True,
                "affiliate_url": aff_link,
                "commission": None,
            }
        else:
            return {"success": False, "error": data.get("message", "Unknown error")}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout — dobara try karein"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ══════════════════════════════════════════════
#   TELEGRAM HANDLERS
# ══════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *EarnKaro Affiliate Bot mein aapka swagat hai!*\n\n"
        "📌 *Kaise use karein:*\n"
        "• Koi bhi Amazon, Flipkart, Myntra link bhejein\n"
        "• Main usse affiliate link mein convert kar dunga\n"
        "• Link automatically group mein bhi post ho sakti hai\n\n"
        "🛒 *Supported Stores:*\n"
        "Amazon • Flipkart • Myntra • AJIO • Nykaa • Meesho aur aur bhi!\n\n"
        "📎 Bas link bhejein aur kamaai shuru karein! 💰",
        parse_mode="Markdown",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Help*\n\n"
        "/start — Bot shuru karein\n"
        "/help  — Yeh message dekhein\n\n"
        "💡 *Sirf link bhejein — baki main karunga!*",
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ka message process karo — links dhoondho aur convert karo"""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    urls = extract_urls(text)

    if not urls:
        await update.message.reply_text(
            "❌ Koi link nahi mila!\n\n"
            "📎 Amazon, Flipkart ya Myntra ka product link bhejein."
        )
        return

    # Supported URLs filter karo
    supported = [u for u in urls if is_supported(u)]
    if not supported:
        await update.message.reply_text(
            "⚠️ Yeh link supported nahi hai.\n\n"
            "✅ Supported: Amazon, Flipkart, Myntra, AJIO, Nykaa, Meesho"
        )
        return

    # Processing message
    processing_msg = await update.message.reply_text(
        f"⏳ {len(supported)} link{'s' if len(supported)>1 else ''} convert ho rahi hai..."
    )

    results = []
    for url in supported:
        platform = detect_platform(url)
        result   = convert_to_affiliate(url)
        results.append((url, platform, result))

    # Delete processing message
    await processing_msg.delete()

    # Results bhejo
    for original_url, platform, result in results:
        if result["success"]:
            aff_url    = result["affiliate_url"]
            commission = result.get("commission")

            reply_text = (
                f"✅ *Affiliate Link Ready!*\n\n"
                f"🏷️ Platform: {platform}\n"
                f"🔗 *Link:*\n`{aff_url}`"
            )
            if commission:
                reply_text += f"\n💰 Commission: *{commission}%*"

            sent = await update.message.reply_text(reply_text, parse_mode="Markdown")

            # Group mein bhi post karo (agar TARGET_GROUP_ID set hai)
            if TARGET_GROUP_ID:
                group_text = (
                    f"🛍️ *{platform} Deal!*\n\n"
                    f"🔗 {aff_url}"
                )
                if commission:
                    group_text += f"\n💰 Extra {commission}% cashback milega!"
                try:
                    await context.bot.send_message(
                        chat_id=TARGET_GROUP_ID,
                        text=group_text,
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.warning(f"Group post failed: {e}")

        else:
            await update.message.reply_text(
                f"❌ *Convert nahi hua*\n"
                f"Platform: {platform}\n"
                f"Error: {result['error']}\n\n"
                f"Original link:\n`{original_url}`",
                parse_mode="Markdown",
            )

# ══════════════════════════════════════════════
#   MAIN — BOT START KARO
# ══════════════════════════════════════════════
def main():
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ ERROR: TELEGRAM_BOT_TOKEN set nahi hai!")
        print("   earnkaro_bot.py mein apna token daalein.")
        return

    if EARNKARO_API_KEY == "YOUR_EARNKARO_API_KEY":
        print("❌ ERROR: EARNKARO_API_KEY set nahi hai!")
        print("   earnkaro_bot.py mein apni API key daalein.")
        return

    print("🚀 EarnKaro Affiliate Bot start ho raha hai...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot chal raha hai! Ctrl+C se band karein.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()