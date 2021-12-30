import textwrap
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from moltin_api import get_cart_by_user_id, get_products


def serialize_cart(cart):
    order_total = cart['meta']['display_price']['with_tax']['formatted']
    products = cart['data']
    serialized_products = []
    for product in products:
        serialized_product = {
            'name': product['name'],
            'product_id': product['id'],
            'description': product['description'],
            'quantity': str(product['quantity']),
            'price_per_unit': product['meta']['display_price']['with_tax']['unit']['formatted'],
            'total_price': product['meta']['display_price']['with_tax']['value']['formatted'],
        }
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
