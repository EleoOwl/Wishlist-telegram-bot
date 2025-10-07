# WishList Telegram Bot (telebot + SQLite)

## Features
- `/start` sends `hwlloworld` with an inline **Show** button
- User command hints: ** Show** (`/show`) and **My bookings** (`/mybookings`)
- **Show** lists item names from an SQLite DB

## Setup
1. **Create a bot** with BotFather and copy the token.
2. **Clone** the project and create a `.env` from the example:
   ```bash
   cp .env.dev .env
   # put your token in BOT_TOKEN=