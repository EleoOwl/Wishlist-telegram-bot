import telebot
from telebot import types
import re
from db import *
from config import ADMIN_USER_ID
from typing import List

def make_show_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text="Show", callback_data="show"))
    return kb

def is_admin(user_id: int) -> bool:
    return ADMIN_USER_ID and int(user_id) == int(ADMIN_USER_ID)

def get_presentlist_markup(owner_user_id: int, callback_command_prefix: str) -> Optional[types.InlineKeyboardMarkup]:
    presents = list_presents(owner_user_id)
    if not presents:
        return None

    kb = types.InlineKeyboardMarkup()
    for present in presents:
        kb.add(types.InlineKeyboardButton(
            text=present["name"],
            callback_data=f"{callback_command_prefix}:{present['id']}"  
        ))
    return kb

def get_userlist_markup(user_id, callback_command_prefix: str) -> types.InlineKeyboardMarkup:
    listed_users = get_user_preferences(user_id)

    if not listed_users:
        return None

    kb = types.InlineKeyboardMarkup()
    for user in listed_users:
        kb.add(types.InlineKeyboardButton(
            text=user["name"],
            callback_data=f"{callback_command_prefix}:{user["id"]}"  
        ))
    return kb

def parse_price(text: str):
    parts = text.split()
    if len(parts) < 2:
        raise ValueError("Price must be '[value] [currency]', e.g. '25 USD'.")

    value_str = parts[0]
    currency = " ".join(parts[1:]).strip()  # allow multi-word currencies just in case

    try:
        return value_str, currency
    except Exception:
        raise ValueError("Price value must be an integer (e.g., 25).")

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

    price_val,currency = parse_price(price_raw)

    if not name:
        raise ValueError("Name cannot be empty.")
    # currency can be empty -> we store None in DB; but here we keep string (can be "")
    return name, description, price_val, currency