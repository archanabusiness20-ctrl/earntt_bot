import os
import logging
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ════════════════════════════
#  LOGGING (Render logs ke liye)
# ════════════════════════════
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ════════════════════════════
#  ENVIRONMENT VARIABLES
# ════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
EARNKARO_API_KEY = os.environ.get("EARNKARO_API_KEY")
EARNKARO_API_URL = os.environ.get("EARNKARO_API_URL", "https://ekaro-api.affiliaters.in/api/converter/public")

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN set nahi hai!")
    exit(1)

if not EARNKARO_API_KEY:
    logger.error("❌ EARNKARO_API_KEY set nahi hai!")
    exit(1)

# ════════════════════════════
#  SUPPORTED PLATFORMS
# ════════════════════════════
SUPPORTED_DOMAINS = [
    "amazon.in", "amzn.in", "amzn.to",
    "flipkart.com", "fkrt.it",
    "myntra.com", "ajio.com", "nykaa.com", "meesho.com"
]

def extract_urls(text: str) -> list:
    pattern = r'https?://[^\s]+'
    return re.findall(pattern, text)

def is_supported(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def detect_platform(url: str) -> str:
    if "amazon" in url or "amzn" in url: return "🛒 Amazon"
    elif "flipkart" in url or "fkrt" in url: return "🏪 Flipkart"
    elif "myntra" in url: return "👗 Myntra"
    elif "ajio" in url: return "👔 AJIO"
    elif "nykaa" in url: return "💄 Nykaa"
    elif "meesho" in url: return "🛍️ Meesho"
    else: return "🔗 Store"

def convert_to_affiliate(original_url: str) -> dict:
    try:
        response = requests.post(
            EARNKARO_API_URL,
            headers={
                "Authorization": f"Bearer {EARNKARO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"deal": original_url, "convert_option": "convert_only"},
            timeout=10,
        )
        data = response.json()
        if response.ok and data.get("success"):
            return {"success": True, "affiliate_url": data.get("data")}
        else:
            return {"success": False, "error": data.get("message", "Unknown error")}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ════════════════════════════
#  TELEGRAM HANDLERS
# ════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send me any Amazon/Flipkart link to get affiliate link.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text("❌ No link found.")
        return

    supported = [u for u in urls if is_supported(u)]
    if not supported:
        await update.message.reply_text("⚠️ Unsupported link. Only Amazon, Flipkart, Myntra, etc.")
        return

    await update.message.reply_text(f"⏳ Converting {len(supported)} link(s)...")

    for url in supported:
        result = convert_to_affiliate(url)
        if result["success"]:
            await update.message.reply_text(
                f"✅ Affiliate Link:\n`{result['affiliate_url']}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Failed: {result['error']}")

# ════════════════════════════
#  MAIN
# ════════════════════════════
def main():
    logger.info("🚀 Bot starting...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot is polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
