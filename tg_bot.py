from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackQueryHandler, CommandHandler, MessageHandler
import re
import logging

from environments import TG_TOKEN
from database import get_database_connection
from moltin_api import (
    get_product_by_id, get_photo_by_id, add_to_cart, delete_item, register_customer
)
from functions import show_menu, show_cart


logger = logging.getLogger(__name__)


def start(bot, update):
    show_menu(bot, update)
    return 'HANDLE_MENU'


def handle_menu(bot, update):
    query = update.callback_query
    if query.data == 'cart':
        show_cart(bot, update)
        return 'HANDLE_CART'
    product = get_product_by_id(query.data)

    product_name = product['name']
    product_price = product['meta']['display_price']['with_tax']['formatted']
    product_description = product['description']
    product_stock = product['meta']['stock']['level']
    photo = get_photo_by_id(query.data)
    product_info = f'{product_name}\n{product_description}\n\n{product_price} per kg (available {product_stock} kg)'

    redis_db.hmset(str(query.message.chat_id), {'current_product': query.data})

    keyboard = [
        [
            InlineKeyboardButton('1kg', callback_data=1),
            InlineKeyboardButton('5kg', callback_data=5),
            InlineKeyboardButton('10kg', callback_data=10),
        ],
        [InlineKeyboardButton('Back', callback_data='back')]
    ]

    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=photo,
        caption=product_info,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    query = update.callback_query
    if query.data == 'back':
        show_menu(bot, update)
        return 'HANDLE_MENU'
    product_id = redis_db.hget(str(query.message.chat_id), 'current_product').decode("utf-8")
    amount = query.data
    add_to_cart(product_id, amount, query.message.chat_id)
    bot.answer_callback_query(
        callback_query_id=query.id,
        show_alert=True,
        text='Item was added successfully'
    )
    return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    query = update.callback_query
    if query.data == 'back':
        show_menu(bot, update)
        return 'HANDLE_MENU'
    elif query.data == 'pay':
        bot.send_message(
            chat_id=query.message.chat_id,
            text='Your order was accepted!\nPlease, enter your email and our managers will contact you'
        )
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        logger.info(f'New order was created')
        return 'WAITING_EMAIL'
    else:
        delete_item(query.message.chat_id, query.data)
        show_cart(bot, update)
        return 'HANDLE_CART'


def handle_email(bot, update):
    user_email = update.message.text.strip()
    # Regex was found here: https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if re.fullmatch(regex, user_email):
        username = update.message.from_user['username']
        register_customer(name=username, email=user_email)
        bot.send_message(
            chat_id=update.message.chat_id,
            text=f'Your email {user_email} was accepted.\nThank you!'
        )
        logger.info(f'New customer {user_email} was created')
        return 'END'
    bot.send_message(
        chat_id=update.message.chat_id,
        text='Please, provide correct email'
    )
    return 'WAITING_EMAIL'


def handle_users_reply(bot, update):
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = redis_db.hget(str(chat_id), 'next_state').decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(bot, update)
        redis_db.hmset(str(chat_id), {'next_state': next_state})
    except Exception as err:
        print(err)


if __name__ == '__main__':
    logger.setLevel(logging.INFO)
    redis_db = get_database_connection()
    updater = Updater(TG_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    logger.info('TG bot was started')
    updater.start_polling()
    updater.idle()
