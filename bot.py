import telebot
from telebot import types
import html
from typing import List

from config import BOT_TOKEN, ADMIN_USER_ID, WEBHOOK_PATH, WEBHOOK_BASE, WEBHOOK_SECRET_TOKEN, APP_HOST, APP_PORT
from db import *
from helpers import *

# --- Bootstrapping ---
init_db()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# --- Public command list (visible to all users) ---
PUBLIC_COMMANDS = [
    types.BotCommand("show", " Show"),
    types.BotCommand("mybookings", "My bookings"),
    types.BotCommand("mywishlist", "My wishlist"),
    types.BotCommand("additem", "Add item to my wishlist")
]
bot.set_my_commands(PUBLIC_COMMANDS)


# --- Admin-specific command list ---
if ADMIN_USER_ID:
    ADMIN_COMMANDS = PUBLIC_COMMANDS + [
        #types.BotCommand("additem", "Add item")
        ]
    try:
        bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=types.BotCommandScopeChat(chat_id=ADMIN_USER_ID)
        )
    except Exception as e:
        print(f"Warning: failed to set admin commands scope: {e}")


# ----- Helpers -----
def send_buttons_list(chat_id: int, items:  List[dict], message: str, callback_command_prefix: str) -> None:
    """Sends an inline keyboard with every present name as a button."""
    if not items:
        bot.send_message(chat_id, "No items found.")
        return

    kb = types.InlineKeyboardMarkup()
    # one button per row
    for p in items:
        kb.add(types.InlineKeyboardButton(
            text=p["name"],
            callback_data=f"{callback_command_prefix}:{p['id']}"  # <= will trigger the details view
        ))
    bot.send_message(chat_id, message, reply_markup=kb)


def show_present(chat_id: int, present_id: int) -> None:
    """Loads a present and shows all fields except giver_chat_id."""
    data = get_present_by_id(present_id)
    if not data:
        bot.send_message(chat_id, "Present not found.")
        return

    # Build an HTML-safe message
    esc = html.escape
    lines = [f"<b>{esc(data['name'] or '')}</b>"]

    if data.get("description"):
        lines.append(f"{esc(data['description'])}")

    # Price + currency in one line if price present
    price = data.get("price")
    currency = data.get("currency") or ""
    if price is not None:
        price_part = f"{price} {esc(currency)}".strip()
        lines.append(f"<b>Price:</b> {price_part}")

    # Optional fields
    if data.get("link"):
        # Show as a clickable link
        url = esc(data["link"], quote=True)
        lines.append(f"<b>Link:</b> <a href=\"{url}\">Open</a>")

    photo_ref = (data.get("photo_url") or "").strip()
    
    booked = data.get("is_booked")
    gifted = data.get("is_gifted")
    kb = types.InlineKeyboardMarkup()

    if (booked and not gifted):
        lines.append(f"\n<b>Booked{' by you' if int(data.get('giver_chat_id') or 0) == int(chat_id) else ''}</b>")
        if int(data.get("giver_chat_id") or 0) == int(chat_id):
            kb.add(types.InlineKeyboardButton(text="Unbook", callback_data=f"unbook:{data['id']}"))
    elif gifted:
          lines.append(f"\n<b>Gifted</b>")

    if (not booked and not gifted):
        kb.add(types.InlineKeyboardButton(text="Book", callback_data=f"book:{data['id']}"))
    
    # --- Owner buttons ---
    if chat_id == data.get("owner_user_id"):
        kb.add(types.InlineKeyboardButton(text="Edit photo", callback_data=f"edit:{data['id']}:photo"))
        kb.add(types.InlineKeyboardButton(text="Edit link", callback_data=f"edit:{data['id']}:link"))
        kb.add(types.InlineKeyboardButton(text="Edit description", callback_data=f"edit:{data['id']}:desc"))
        kb.add(types.InlineKeyboardButton(text="Edit price", callback_data=f"edit:{data['id']}:price"))
        kb.add(types.InlineKeyboardButton(text="Delete", callback_data=f"delete:{data['id']}"))
        kb.add(types.InlineKeyboardButton(text="Mark gifted", callback_data=f"gift:{data['id']}"))

    if photo_ref:
        bot.send_photo(chat_id, photo_ref, caption="\n".join(lines), parse_mode="HTML", reply_markup=kb)
        return
    bot.send_message(chat_id, "\n".join(lines), disable_web_page_preview=True, reply_markup=kb)

# --- Handlers ---

@bot.message_handler(commands=["start"])
def on_start(msg: types.Message):
    bot.send_message(
        msg.chat.id,
        "Hello! This bot allows you to know preferred gifts for Owl. Press /show to list preset items. You can book for gist the one you like or unbook if you changed your mind.",
        reply_markup=make_show_keyboard()
    )

@bot.message_handler(commands=["show"])
def on_show_command(msg: types.Message):
    bot.answer_callback_query(msg.id)
    
    bot.answer_callback_query(msg.id, "Please choose user wishlist to show or type telegram username to see if created:")

    rb = get_user_preferences(msg.from_user.id, "showwishlist")
    if not rb:
        bot.send_message(msg.chat.id, "Your wishlist is empty. Add items with /additem.")
        return
    bot.send_message(msg.chat.id, "Select a user: ", reply_markup= rb)

@bot.callback_query_handler(func=lambda c: c.data == "show")
def on_show_callback(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    
    bot.answer_callback_query(call.id, "Please choose user wishlist to show or type telegram username to see if created:")

    rb = get_user_preferences(call.from_user.id, "showwishlist")
    if not rb:
        bot.send_message(call.message.chat.id, "Your wishlist is empty. Add items with /additem.")
        return
    bot.send_message(call.message.chat.id, "Select a user: ", reply_markup= rb)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("showwishlist:"))
def on_show_callback(call: types.CallbackQuery):
    try:
        user_id = int(call.data.split(":", 1)[1])
    except Exception:
        bot.answer_callback_query(call.id, "Invalid user id.")
        return

    rb = get_presentlist_markup(user_id, "present")
    if not rb:
        bot.send_message(call.message.chat.id, "User wishlist is empty :(")
        return
    bot.send_message(call.message.chat.id, "Select a present: ", reply_markup= rb)


@bot.message_handler(commands=["mywishlist"])
def on_show_command(msg: types.Message):
    rb = get_presentlist_markup(msg.from_user.id, "present")
    if not rb:
        bot.send_message(msg.chat.id, "Your wishlist is empty. Add items with /additem.")
        return
    bot.send_message(msg.chat.id, "Select a present: ", reply_markup= rb)

@bot.message_handler(commands=["mybookings"])
def on_show_command(msg: types.Message):
    
    
    send_buttons_list(msg.chat.id, list_booked_presents(msg.chat.id), "Booked by you: ")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("present:"))
def on_present_clicked(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    try:
        present_id = int(call.data.split(":", 1)[1])
    except Exception:
        bot.send_message(call.message.chat.id, "Invalid present id.")
        return
    show_present(call.message.chat.id, present_id)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("book:"))
def on_book_clicked(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    try:
        present_id = int(call.data.split(":", 1)[1])
    except Exception:
        bot.answer_callback_query(call.id, "Invalid present id.")
        return

    res = try_book_present(present_id, giver_chat_id=chat_id)
    
    if res:
        bot.answer_callback_query(call.id, "Booked!")
    else:
        bot.answer_callback_query(call.id, "Cannot book this right now.")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("unbook:"))
def on_unbook_clicked(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    try:
        present_id = int(call.data.split(":", 1)[1])
    except Exception:
        bot.answer_callback_query(call.id, "Invalid present id.")
        return

    res = try_unbook_present(present_id, chat_id)
    
    if res:
        bot.answer_callback_query(call.id, "Unbooked! Now you are free of this obligation")
    else:
        bot.answer_callback_query(call.id, "Cannot unbook this right now.")

@bot.message_handler(commands=["additem"])
def on_add_item_command(msg: types.Message):
    instruction = "Please send the present in this format or type /cancel to abort:\n\n"
    template = (
        "Name: Lego Technic Car\n"
        "Description: Red sports model\n"
        "Price: 120 EUR\n\n"
        )
    bot.send_message(msg.chat.id, instruction)
    bot.send_message(msg.chat.id, template)
    bot.register_next_step_handler(msg, handle_add_item_payload)

def handle_add_item_payload(msg: types.Message):
    if not msg.text:
        sent = bot.reply_to(msg, "I need text in the required format. Try again or /cancel.")
        bot.register_next_step_handler(sent, handle_add_item_payload)
        return
    if msg.text.strip().lower() == "/cancel":
        bot.reply_to(msg, "Cancelled.")
        return

    try:
        name, description, price_val, currency = parse_additem_payload(msg.text)
        new_id = create_present(name=name, description=description, price=price_val, currency=currency, owner_user_id  = msg.from_user.id)
        create_user(msg.from_user.id, msg.from_user.username or msg.from_user.full_name or "")
        bot.reply_to(
            msg,
            f" Present successfully added .\n\n<b>Saved:</b>\n"
            f"- Name: {name}\n"
            f"- Description: {description}\n"
            f"- Price: {price_val} {currency or ''}\n\n"
        )
    except ValueError as e:
        sent = bot.reply_to(msg, f" {e}\n\nPlease correct and resend, or /cancel.")
        bot.register_next_step_handler(sent, handle_add_item_payload)
    except Exception as e:
        sent = bot.reply_to(msg, f" Unexpected error: {e}\nTry again, or /cancel.")
        bot.register_next_step_handler(sent, handle_add_item_payload)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("delete:"))
def on_delete_clicked(call: types.CallbackQuery):
    # Allow only admin to continue the flow
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return
    
    chat_id = call.message.chat.id
    
    try:
        present_id = int(call.data.split(":", 1)[1])
    except Exception:
        bot.answer_callback_query(call.id, "Invalid present id.")
        return

    res = try_delete_present(present_id)
    
    if res:
        bot.answer_callback_query(call.id, "Deleted!")
    else:
        bot.answer_callback_query(call.id, "Cannot delete this right now.")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("gift:"))
def on_gift_clicked(call: types.CallbackQuery):
    # Allow only admin to continue the flow
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return

    chat_id = call.message.chat.id
    
    try:
        present_id = int(call.data.split(":", 1)[1])
    except Exception:
        bot.answer_callback_query(call.id, "Invalid present id.")
        return

    res = try_gift_present(present_id)
    
    if res:
        bot.answer_callback_query(call.id, "Changed status to gifted!")
    else:
        bot.answer_callback_query(call.id, "Cannot change status right now.")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("edit:"))
def on_edit_clicked(call: types.CallbackQuery):
    # Allow only admin to continue the flow
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return
    
    chat_id = call.message.chat.id
    try:
        _, present_id, edit_type = call.data.split(":", 2)  # photo, link, desc, price
        
    except Exception:
        bot.answer_callback_query(call.id, "Invalid present id.")
        return

    if edit_type not in {"photo", "link", "desc", "price"}:
        bot.answer_callback_query(call.id, "Unsupported edit type.")
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(chat_id, f"Editing {edit_type}. Please send the new value or /cancel to abort.")
    
    bot.register_next_step_handler(
        msg,
        handle_edit_item_payload,
        present_id,
        edit_type
    )
    

def handle_edit_item_payload(msg: types.Message, present_id: int, edit_type: str):
    chat_id = msg.chat.id

    # cancellation
    if msg.text and msg.text.strip().lower() == "/cancel":
        bot.reply_to(msg, "Cancelled.")
        return

    try:
        if edit_type == "photo":
            # Prefer a real photo or image document
            new_value = None
            if getattr(msg, "content_type", "") == "photo" and msg.photo:
                new_value = msg.photo[-1].file_id
            elif getattr(msg, "content_type", "") == "document" and msg.document and (msg.document.mime_type or "").startswith("image/"):
                new_value = msg.document.file_id
            elif msg.text:
                # Allow pasting a file_id or URL as a fallback
                new_value = msg.text.strip()

            if not new_value:
                sent = bot.reply_to(msg, "Please send a photo (or image file), or paste a valid file_id/URL. /cancel to abort.")
                bot.register_next_step_handler(sent, handle_edit_item_payload, present_id, edit_type)
                return

            set_present_photo_url(present_id, new_value)
            bot.reply_to(msg, "Photo updated.")

        elif edit_type == "link":
            if not msg.text or not msg.text.strip():
                sent = bot.reply_to(msg, "Please send a non-empty link. /cancel to abort.")
                bot.register_next_step_handler(sent, handle_edit_item_payload, present_id, edit_type)
                return
            set_present_link(present_id, msg.text.strip())
            bot.reply_to(msg, "Link updated.")

        elif edit_type == "desc":
            if msg.text is None:
                sent = bot.reply_to(msg, "Please send text for the description. /cancel to abort.")
                bot.register_next_step_handler(sent, handle_edit_item_payload, present_id, edit_type)
                return
            set_present_description(present_id, msg.text)
            bot.reply_to(msg, "Description updated.")
        elif edit_type == "price":
            if msg.text is None:
                sent = bot.reply_to(msg, "Please send text for the price in format: 10 EUR. /cancel to abort.")
                bot.register_next_step_handler(sent, handle_edit_item_payload, present_id, edit_type)
                return
            try: 
                price_val, price_currency = parse_price(msg.text)
                set_present_price(present_id, price_val)
                set_present_currency(present_id, price_currency)
                bot.reply_to(msg, "Price updated.") 
            except ValueError as e:
                print('valueerror before')
                sent = bot.reply_to(msg, f"Invalid price: {e}\nPlease correct and resend, or /cancel.")
                print('valueerror reply')
                bot.register_next_step_handler(msg, handle_edit_item_payload, present_id, edit_type)
                return

        else:
            bot.reply_to(msg, "Unsupported edit type.")

    except Exception as e:
        # Friendly error, re-prompt
        sent = bot.reply_to(msg, f"Update failed: {e}\nPlease try again, or /cancel.")
        bot.register_next_step_handler(sent, handle_edit_item_payload, present_id, edit_type)



@bot.message_handler(commands=["cancel"])
def on_cancel(msg: types.Message):
    bot.reply_to(msg, "Cancelled.")


# --- Entry point: webhook (Flask) or polling based on env ---

import time

def run_polling_mode(bot: telebot.TeleBot):
    try:
        bot.remove_webhook()
    except Exception:
        pass
    bot.infinity_polling(skip_pending=True)

def run_webhook_mode(bot: telebot.TeleBot):
    # Lazy-import Flask so polling users don't need it installed
    try:
        from flask import Flask, request, abort
        from telebot import types as tb_types
    except Exception as e:
        print(f"[warn] Flask not available ({e}). Falling back to polling.")
        return run_polling_mode(bot)

    app = Flask(__name__)

    @app.get("/health")
    def health():
        return "ok"

    @app.post(WEBHOOK_PATH)
    def telegram_webhook():
        # Verify Telegram secret header
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if WEBHOOK_SECRET_TOKEN and secret != WEBHOOK_SECRET_TOKEN:
            abort(403)

        upd_json = request.get_json(silent=True) or {}
        if not upd_json:
            return "ok"
        update = tb_types.Update.de_json(upd_json)
        bot.process_new_updates([update])
        return "ok"

    # (Re)set webhook to HTTPS endpoint
    try:
        bot.remove_webhook()
    except Exception:
        pass
    time.sleep(0.3)
    bot.set_webhook(url=f"{WEBHOOK_BASE}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET_TOKEN)

    # Bind address/port for the local app
    app.run(host=APP_HOST, port=int(APP_PORT))

def should_use_webhook() -> bool:
    return bool(WEBHOOK_BASE)

def main():
    global bot 
    if should_use_webhook():
        run_webhook_mode(bot)
    else:
        run_polling_mode(bot)

if __name__ == "__main__":
    main()