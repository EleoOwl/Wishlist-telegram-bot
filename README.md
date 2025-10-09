# WishList Telegram Bot (telebot + SQLite)

## Features
- `/start` sends short invitation message with an inline **Show** button
- User command hints: **Show** (`/show`) and **My bookings** (`/mybookings`)
- **Show** lists item names from an SQLite DB
- **My bookings** lists user-specific bookings from the DB
- User can book/unbook items via inline buttons
- Admin command hints: **Add item** (`/additem`), **Delete item** (`/delete:itemId`), **Update item** (`/update:name|desc|link|photo:itemId`), **Mark as gifted** (`/gift:itemId`)
- Admin-only access to add/update/delete items 
-  Admin can mark items as gifted



## Setup
1. **Create a bot** with BotFather and copy the token.
2. **Clone** the project and create a `.env` file from the example:
 
For polling mode: 
 
   ```bash
   # put your token in BOT_TOKEN=123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   # optionally set DB_PATH= to your SQLite DB path
   # put your admin user ID in ADMIN_USER_ID=123456789
   ```
For webhook mode add next : 
   ```bash
   # WEBHOOK_BASE=https://bot.example.com
   # WEBHOOK_SECRET_TOKEN=some-long-random-string
   # APP_HOST=127.0.0.1
   # APP_PORT=8080
   ```