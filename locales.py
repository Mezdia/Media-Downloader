
# Localization Dictionary
LOCALES = {
    "en": {
        "welcome": "Welcome to Media Downloader Bot! 🎬\nSend me a link from YouTube or Instagram to download.",
        "help": "Help:\nSend a link to download.\n/start - Restart bot\n/lang - Change language\n/stats - View stats (Admin)",
        "downloading": "Downloading... ⬇️",
        "uploading": "Uploading to Telegram... 🚀",
        "completed": "Download completed! ✅",
        "error": "Error: {}",
        "invalid_url": "Invalid URL. Please send a valid YouTube or Instagram link.",
        "select_lang": "Please select your language:",
        "lang_set": "Language set to English 🇺🇸",
        "not_admin": "You are not authorized to use this command.",
        "stats_msg": "📊 **Bot Statistics**\n\nUsers: {users}\nDownloads: {downloads}",
        "broadcast_sent": "Broadcast sent to {count} users.",
        "banned": "You have been banned from using this bot.",
        "processing": "Processing... ⚙️",
        "searching": "Searching... 🔎",
        "found": "🎬 **{title}**\n\nSelect quality:",
        "quality_best": "Best Quality 🌟",
        "quality_1080": "1080p 🖥️",
        "quality_720": "720p 📱",
        "quality_audio": "Audio Only 🎵",
    },
    "fa": {
        "welcome": "به ربات دانلودر مدیا خوش آمدید! 🎬\nلینک یوتیوب یا اینستاگرام خود را ارسال کنید.",
        "help": "راهنما:\nلینک را برای دانلود ارسال کنید.\n/start - شروع مجدد\n/lang - تغییر زبان\n/stats - آمار (ادمین)",
        "downloading": "در حال دانلود... ⬇️",
        "uploading": "در حال آپلود به تلگرام... 🚀",
        "completed": "دانلود کامل شد! ✅",
        "error": "خطا: {}",
        "invalid_url": "لینک نامعتبر است. لطفا لینک معتبر یوتیوب یا اینستاگرام ارسال کنید.",
        "select_lang": "لطفا زبان خود را انتخاب کنید:",
        "lang_set": "زبان به فارسی تغییر کرد 🇮🇷",
        "not_admin": "شما مجاز به استفاده از این دستور نیستید.",
        "stats_msg": "📊 **آمار ربات**\n\nکاربران: {users}\nدانلودها: {downloads}",
        "broadcast_sent": "پیام همگانی به {count} کاربر ارسال شد.",
        "banned": "شما از استفاده از ربات مسدود شده‌اید.",
        "processing": "در حال پردازش... ⚙️",
        "searching": "در حال جستجو... 🔎",
        "found": "🎬 **{title}**\n\nکیفیت را انتخاب کنید:",
        "quality_best": "بهترین کیفیت 🌟",
        "quality_1080": "1080p 🖥️",
        "quality_720": "720p 📱",
        "quality_audio": "فقط صدا 🎵",
    }
}

def t(key: str, lang: str = "fa", **kwargs) -> str:
    """Get translated string."""
    lang_dict = LOCALES.get(lang, LOCALES["en"])
    text = lang_dict.get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
