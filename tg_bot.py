from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackQueryHandler, CommandHandler, MessageHandler
import textwrap
import re
import logging

from environments import TG_TOKEN
from database import get_database_connection
from moltin_api import (
    get_products, get_product_by_id, get_photo_by_id, add_to_cart, get_cart_by_user_id, delete_item, register_customer
)


logger = logging.getLogger(__name__)


def serialize_cart(cart):
    order_total = cart['meta']['display_price']['with_tax']['formatted']
    products = cart['data']
    serialized_products = []
    for product in products:
        serialized_product = dict()
        serialized_product['name'] = product['name']
        serialized_product['product_id'] = product['id']
        serialized_product['description'] = product['description']
        serialized_product['quantity'] = str(product['quantity'])
        serialized_product['price_per_unit'] = product['meta']['display_price']['with_tax']['unit']['formatted']
        serialized_product['total_price'] = product['meta']['display_price']['with_tax']['value']['formatted']
        serialized_products.append(serialized_product)
    return {'order_total': order_total, 'products': serialized_products}


def show_menu(bot, update):
    query = update.callback_query
    keyboard = []
    products = get_products()

    for product in products:
        keyboard.append([InlineKeyboardButton(product['name'], callback_data=product['id'])])

    if query:
        chat_id = query.message.chat_id
    else:
        chat_id = update.message.chat_id
    user_cart = get_cart_by_user_id(chat_id)

    if user_cart['data']:
        keyboard.append([InlineKeyboardButton('CART', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        bot.send_message(
            chat_id=query.message.chat_id,
            reply_markup=reply_markup,
            text='Please choose:'
        )
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    else:
        update.message.reply_text(text='Please choose:', reply_markup=reply_markup)


def show_cart(bot, update):
    query = update.callback_query
    cart = get_cart_by_user_id(query.message.chat_id)
    serialized_cart = serialize_cart(cart)
    message = f'<b>Total price: <i>{serialized_cart["order_total"]}</i></b>\n\n<b>List of items</b>:\n'
    keyboard = [[
        InlineKeyboardButton('PAY', callback_data='pay'),
        InlineKeyboardButton('BACK', callback_data='back')
    ]]

    for product in serialized_cart['products']:
        product_text = f'''\
            {product["name"]}
            <b>Price</b>: {product["price_per_unit"]} per kg
            <b>Ordered</b>: {product["quantity"]}kg 
            <b>Sum</b>: {product["total_price"]}\n
        '''
        message += textwrap.dedent(product_text)
        keyboard.append([InlineKeyboardButton(
            f'Remove {product["name"]} ({product["quantity"]}kg)',
            callback_data=product['product_id']
        )])
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(
        chat_id=query.message.chat_id,
        text=message,
        reply_markup=reply_markup,
        parse_mode='html'
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


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
