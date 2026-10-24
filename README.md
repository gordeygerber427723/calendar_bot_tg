# 📅 Calendar Bot

A Telegram bot built with Python that helps you manage important events and receive timely reminders.

## ✨ Features

- 📝 Create events with a title, date, time, and description.
- 📋 View your saved events.
- 🗑️ Delete events.
- ⏰ Receive daily reminders with the number of days remaining until an event.
- 🔔 Receive a notification at the scheduled time on the event date.
- 🌍 Configure your time zone for accurate notifications.
- 💾 Store events in an SQLite database.

## 🛠️ Technologies

- Python
- [aiogram 3](https://docs.aiogram.dev/en/latest/) — Telegram Bot API framework
- SQLite — database
- `python-dotenv` — environment variable management

## 📋 Requirements

- Python 3.10 or newer
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- pip

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/gordeygerber427723/calendar_bot_tg.git
cd calendar_bot_tg
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project directory:

```env
BOT_TOKEN=your_telegram_bot_token
TELEGRAM_PROXY=http://127.0.0.1:10809
```

Replace `your_telegram_bot_token` with your actual token from BotFather.

The proxy setting is optional. If you do not need a proxy, configure the project accordingly.

**Security:** Never publish your `.env` file or share your Telegram bot token.

### 5. Run the bot

```bash
python bot.py
```

The SQLite database is initialized automatically when the application starts. A new database will initially contain no events.

## 🗄️ Database

The bot uses SQLite to store events and user settings. The database file is created locally and should not be committed to the repository.

Keep a backup of your database if you need to preserve your saved events.

## 🔔 Notifications

The bot supports two types of reminders:

- **Daily reminders:** Notify users about upcoming events and the remaining number of days, when enabled for an event.
- **Event-time notifications:** Notify users on the event date at the scheduled time, independently of the daily reminder setting.

Notifications use the user's configured time zone.

## 📁 Project Structure

```text
calendar_bot_tg/
├── bot.py
├── database.py
├── requirements.txt
└── .env
```

The `.venv/`, `.env`, and `calendar.db` files are intended to remain local and should not be committed.

## 📄 License

No license has been specified yet. All rights reserved unless a license is added to this repository.
