import telebot
from telebot import types
import html
from typing import List

from config import BOT_TOKEN, ADMIN_USER_ID
from db import init_db, create_present, get_present_by_id, try_book_present, list_presents, list_booked_presents,try_delete_present
from helpers import make_show_keyboard, is_admin, parse_additem_payload

# --- Bootstrapping ---
init_db()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# --- Public command list (visible to all users) ---
PUBLIC_COMMANDS = [
    types.BotCommand("show", " Show"),
    types.BotCommand("mybookings", "My bookings"),
]
bot.set_my_commands(PUBLIC_COMMANDS)


# --- Admin-specific command list (only for the admin's private chat) ---
# Uses command scopes to show an extra "Edit list" command to the admin user only.
if ADMIN_USER_ID:
    ADMIN_COMMANDS = PUBLIC_COMMANDS + [
        types.BotCommand("additem", "Add item")
        ]
    try:
        bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=types.BotCommandScopeChat(chat_id=ADMIN_USER_ID)
        )
    except Exception as e:
        # Non-fatal; commands still work even if Telegram refuses the scope (e.g., user hasn't opened the bot)
        print(f"Warning: failed to set admin commands scope: {e}")


# ----- Helpers -----
def send_presents_list(chat_id: int, presents:  List[dict], message: str) -> None:
    """Sends an inline keyboard with every present name as a button."""
    if not presents:
        bot.send_message(chat_id, "No presents found.")
        return

    kb = types.InlineKeyboardMarkup()
    # one button per row; you can group if you prefer
    for p in presents:
        kb.add(types.InlineKeyboardButton(
            text=p["name"],
            callback_data=f"present:{p['id']}"  # <= will trigger the details view
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
        lines.append(f"<b>Description:</b> {esc(data['description'])}")

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
        lines.append(f"<b>Booked</b>{' by you' if int(data.get("giver_chat_id") or 0) == int(chat_id) else ''}")
    else:
      if gifted:
          lines.append(f"<b>Gifted</b>")

    if (not booked and not gifted):
        kb.add(types.InlineKeyboardButton(text="Book", callback_data=f"book:{data['id']}"))
    print(f"booked {booked} gifted {gifted}")
    
    #/// Admin buttons
    if is_admin(chat_id):
        kb.add(types.InlineKeyboardButton(text="Edit photo", callback_data=f"edit:{data['id']}:photo"))
        kb.add(types.InlineKeyboardButton(text="Edit link", callback_data=f"edit:{data['id']}:link"))
        kb.add(types.InlineKeyboardButton(text="Edit description", callback_data=f"book:{data['id']}:desc"))
        kb.add(types.InlineKeyboardButton(text="Edit name", callback_data=f"book:{data['id']}:desc"))
        kb.add(types.InlineKeyboardButton(text="Delete", callback_data=f"delete:{data['id']}"))

    if(photo_ref):
        bot.send_photo(chat_id, photo_ref, caption="\n".join(lines), parse_mode="HTML", reply_markup=kb)
        return
    bot.send_message(chat_id, "\n".join(lines), disable_web_page_preview=True, reply_markup=kb)

# --- Handlers ---

@bot.message_handler(commands=["start"])
def on_start(msg: types.Message):
    # The user asked for "hwlloworld" exactly; keeping that spelling.
    bot.send_message(
        msg.chat.id,
        "hwlloworld",
        reply_markup=make_show_keyboard()
    )

@bot.message_handler(commands=["show"])
def on_show_command(msg: types.Message):
    send_presents_list(msg.chat.id, list_presents(), "Select a present: ")

@bot.callback_query_handler(func=lambda c: c.data == "show")
def on_show_callback(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    send_presents_list(call.message.chat.id, list_presents(), "Select a present: ")

@bot.message_handler(commands=["mybookings"])
def on_show_command(msg: types.Message):
    send_presents_list(msg.chat.id, list_booked_presents(msg.chat.id), "Booked by you: ")

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

    # Update the existing message in-place to reflect the new state
    show_present(chat_id, present_id, edit_message_id=call.message.message_id)


@bot.message_handler(commands=["mybookings"])
def on_my_bookings(msg: types.Message):
    # Placeholder template logic - customize later
    bot.send_message(msg.chat.id, "You have no bookings yet.")

@bot.message_handler(commands=["additem"])
def on_add_item_command(msg: types.Message):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "Sorry, this command is only available to the admin.")
        return

    instruction = (
        "Please send the present in this format:\n"
         "Name: Lego Technic Car\n"
        "Description: Red sports model\n"
        "Price: 120 EUR\n\n"
        "Or type /cancel to abort."
    )
    bot.send_message(msg.chat.id, instruction)
    bot.register_next_step_handler(msg, handle_add_item_payload)

def handle_add_item_payload(msg: types.Message):
    # Allow only admin to continue the flow
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "Not authorized.")
        return
    if not msg.text:
        sent = bot.reply_to(msg, "I need text in the required format. Try again or /cancel.")
        bot.register_next_step_handler(sent, handle_add_item_payload)
        return
    if msg.text.strip().lower() == "/cancel":
        bot.reply_to(msg, "Cancelled.")
        return

    try:
        name, description, price_val, currency = parse_additem_payload(msg.text)
        new_id = create_present(name=name, description=description, price=price_val, currency=currency)
        bot.reply_to(
            msg,
            f" Added present (id {new_id}).\n\n<b>Saved:</b>\n"
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
def on_book_clicked(call: types.CallbackQuery):
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

    # Update the existing message in-place to reflect the new state
    show_present(chat_id, present_id, edit_message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("edit:"))
def on_edit_clicked(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    try:
        present_id = int(call.data.split(":", 2)[1])
        edit_type = call.data.split(":", 2)[2]  # photo, link, desc, name
    except Exception:
        bot.answer_callback_query(call.id, "Invalid present id.")
        return

    bot.send_message(chat_id, f"Editing {edit_type}. Please send the new value or /cancel to abort.")
    bot.register_next_step_handler(msg, handle_edit_item_payload)
    
    if res:
        bot.answer_callback_query(call.id, "Updated!")
    else:
        bot.answer_callback_query(call.id, "Cannot update this right now.")

    # Update the existing message in-place to reflect the new state
    show_present(chat_id, present_id, edit_message_id=call.message.message_id)


@bot.message_handler(commands=["cancel"])
def on_cancel(msg: types.Message):
    bot.reply_to(msg, "Cancelled.")


# --- Entry point ---

def main():
    # Polling is simple for development; switch to webhooks in production
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    main()