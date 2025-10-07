import telebot
from telebot import types
import re
from db import init_db, create_present
from config import ADMIN_USER_ID

def make_show_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text="Show", callback_data="show"))
    return kb

def is_admin(user_id: int) -> bool:
    return ADMIN_USER_ID and int(user_id) == int(ADMIN_USER_ID)


def parse_additem_payload(text: str):
    """
    Expected format (case-insensitive keys):
    Name: <present_name>
    Description: <present_description>
    Price: <price_value> <price_currency>

    Returns: (name: str, description: str, price: int, currency: str)
    Raises ValueError on bad input.
    """
    if not text:
        raise ValueError("Empty message")

    # Use case-insensitive line matches
    name_m = re.search(r'(?mi)^\s*name\s*:\s*(.+)\s*$', text)
    desc_m = re.search(r'(?mi)^\s*description\s*:\s*(.+)\s*$', text)
    price_m = re.search(r'(?mi)^\s*price\s*:\s*(.+)\s*$', text)

    if not name_m or not desc_m or not price_m:
        raise ValueError("Expected three lines starting with Name:, Description:, and Price:.")

    name = name_m.group(1).strip()
    description = desc_m.group(1).strip()
    price_raw = price_m.group(1).strip()

    # Price format: "<value> <currency>" — value then space then currency name
    parts = price_raw.split()
    if len(parts) < 2:
        raise ValueError("Price must be '<value> <currency>', e.g. '25 USD'.")

    value_str = parts[0]
    currency = " ".join(parts[1:]).strip()  # allow multi-word currencies just in case

    try:
        price_val = int(value_str)
    except Exception:
        raise ValueError("Price value must be an integer (e.g., 25).")

    if not name:
        raise ValueError("Name cannot be empty.")
    # currency can be empty -> we store None in DB; but here we keep string (can be "")
    return name, description, price_val, currency