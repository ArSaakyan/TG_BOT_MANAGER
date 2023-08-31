# - - - - - [ IMPORT ] - - - - -

import asyncio
import configparser
import sqlite3
import random
import re
import logging

from io import BytesIO

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import LeaveChannelRequest, JoinChannelRequest
from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, PhoneCodeExpiredError, FloodWaitError, SessionPasswordNeededError, PasswordHashInvalidError


# - - - - - [ \IMPORT ] - - - - -





# - - - - - [ CONFIG ] - - - - -

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('settings.ini')

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

loop = asyncio.get_event_loop()

APP_API_ID = config.get('TELEGRAM-APP', 'api_id')
APP_API_HASH = config.get('TELEGRAM-APP', 'api_hash')
BOT_ACCESS_TOKEN = config.get('TELEGRAM-BOT', 'access_token')

client = TelegramClient(None, api_id=APP_API_ID, api_hash=APP_API_HASH)

accounts = {}

# - - - - - [ \CONFIG ] - - - - -





# - - - - - [ BOT CONFIG ] - - - - -

bot = Bot(token=BOT_ACCESS_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# - - - - - [ \BOT CONFIG ] - - - - -





# - - - - - [ SQL ] - - - - -

cursor.execute("""
CREATE TABLE IF NOT EXISTS `accounts` (
    `id` integer primary key,
    `id_telegram` integer unique not null,
    `phone` integer unique not null,
    `name` varchar not null,
    `surname` varchar default('-'),
    `session_string` text unique not null,
    `text_message` text default('-'),
    `note` varchar default('-')
)
""")
conn.commit()

# - - - - - [ \SQL ] - - - - -





# - - - - - [ FSM ] - - - - -

class FSM_NewAccount(StatesGroup):
    phone = State()
    code = State()
    password = State()

class FSM_Progress(StatesGroup):
    addGroups = State()
    delGroups = State()
    editMessage = State()
    editNote = State()

class FSM_Settings(StatesGroup):
    send = State()
    cycle = State()
    join = State()
    leave = State()

# - - - - - [ \FSM ] - - - - -





# - - - - - [ DEF ] - - - - -

def data2text(arr, text, delimiter=':'):
    for key, value in arr.items():
        text = text.replace(f'{delimiter}{key}{delimiter}', f'{value}')
    return text



async def get_groups(phone):
    if phone in accounts.keys():
        try:
            arr_dialogs = []
            dialogs = accounts[phone]['connect'].iter_dialogs()

            async for dialog in dialogs:
                if dialog.is_group and dialog.is_channel:
                    arr_dialogs.append(dialog.id)

        finally:
            return arr_dialogs

# - - - - - [ \DEF ] - - - - -





# - - - - - [ TEXT ] - - - - -

text_main = '👾 SPAM BOT 👾'

text_account_info = '''
🆔 Account #:id: | :id_telegram:
👤 Name: :name: :surname:
📱 Phone: +:phone:
📌️ Note: :note:

✉️ Message:
:text_message:

▶️ Status: :status:
'''

# - - - - - [ \TEXT ] - - - - -





# - - - - - [ KEYBOARD ] - - - - -

# TEXT FOR KEYBOARD

bt_accounts = '👤 ACCOUNTS'
bt_settings = '⚙️ SETTINGS'
bt_cancel = '❌ CANCEL'


bt_add_account = '👥 ADD Account'
bt_del_account = '🗑 DELETE Account'

bt_start_spam = '📢 START Spam 🟢'
bt_stop_spam = '📢 STOP Spam 🔴'

bt_add_groups = '💬 ADD Groups'
bt_list_groups = '📋 LIST Groups'
bt_del_groups = '🧹 DELETE Groups'

bt_edit_note = '📌 EDIT Note'
bt_edit_message = '🖋 EDIT Message'

bt_send = '✉️ Send Message'
bt_cycle = '🌀 Start next Cycle'
bt_join = '👥 Join to Group'
bt_leave = '❌ Leave Group'



# DEF KEYBOARD

def keyboard_main():
    b_accounts = KeyboardButton(text=bt_accounts)
    b_settings = KeyboardButton(text=bt_settings)
    return ReplyKeyboardMarkup(resize_keyboard=True).add(b_settings, b_accounts)

def keyboard_cancel():
    b_cancel = KeyboardButton(text=bt_cancel)
    return ReplyKeyboardMarkup(resize_keyboard=True).add(b_cancel)


def keyboard_stop_spam(phone):
    b_stop_spam = InlineKeyboardButton(text=bt_stop_spam, callback_data=f'{bt_stop_spam} {phone}')
    return InlineKeyboardMarkup(resize_keyboard=True).add(b_stop_spam)


def keyboard_settings():
    b_delay_send = InlineKeyboardButton(text=bt_send, callback_data=bt_send)
    b_delay_cycle = InlineKeyboardButton(text=bt_cycle, callback_data=bt_cycle)
    b_delay_join = InlineKeyboardButton(text=bt_join, callback_data=bt_join)
    b_delay_leave = InlineKeyboardButton(text=bt_leave, callback_data=bt_leave)
    return InlineKeyboardMarkup(resize_keyboard=True).add(b_delay_send, b_delay_cycle).add(b_delay_join, b_delay_leave)

def keyboard_account(phone):
    b_start_stop_spam = InlineKeyboardButton(text=bt_start_spam, callback_data=f'{bt_start_spam} {phone}')
    b_add_groups = InlineKeyboardButton(text=bt_add_groups, callback_data=f'{bt_add_groups} {phone}')
    b_del_groups = InlineKeyboardButton(text=bt_del_groups, callback_data=f'{bt_del_groups} {phone}')
    b_list_groups = InlineKeyboardButton(text=bt_list_groups, callback_data=f'{bt_list_groups} {phone}')
    b_edit_message = InlineKeyboardButton(text=bt_edit_message, callback_data=f'{bt_edit_message} {phone}')
    b_edit_note = InlineKeyboardButton(text=bt_edit_note, callback_data=f'{bt_edit_note} {phone}')
    b_del_account = InlineKeyboardButton(text=bt_del_account, callback_data=f'{bt_del_account} {phone}')
    return InlineKeyboardMarkup(resize_keyboard=True).add(b_start_stop_spam).add(b_del_groups, b_add_groups).add(b_list_groups).add(b_edit_note, b_edit_message).add(b_del_account)

def keyboard_add_account():
    b_add_account = InlineKeyboardButton(text=bt_add_account, callback_data=bt_add_account)
    return InlineKeyboardMarkup(resize_keyboard=True).add(b_add_account)

def keyboard_del_account(phone):
    b_delAccount = InlineKeyboardButton(text=bt_del_account, callback_data=f'{bt_del_account} {phone}')
    return InlineKeyboardMarkup(resize_keyboard=True).add(b_delAccount)

# - - - - - [ \KEYBOARD ] - - - - -





# - - - - - [ DP ] - - - - -

@dp.message_handler(lambda message: message.from_user.id != int(config.get('ADMIN', 'telegram_id')))
async def message_check_admin(message: types.Message):
    await message.reply('You are not an Administrator 😏')

@dp.callback_query_handler(lambda call: call.from_user.id != int(config.get('ADMIN', 'telegram_id')))
async def callback_check_admin(call: types.CallbackQuery):
    await call.message.answer('You are not an Administrator 😏')



@dp.message_handler(text=bt_cancel, state='*')
@dp.message_handler(commands=['start'])
async def message_command_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(text=text_main, reply_markup=keyboard_main())


@dp.message_handler(text=bt_settings)
async def message_settings(message: types.Message):
    await message.answer(text='⚙️ SETTINGS', reply_markup=keyboard_settings())

@dp.message_handler(text=bt_accounts)
async def message_accounts(message: types.Message):
    cursor.execute("SELECT * FROM `accounts`")
    rows = cursor.fetchall()
    arr_accounts_db = [dict(zip([col[0] for col in cursor.description], row)) for row in rows] if rows else []

    for account in arr_accounts_db:
        try:
            account['status'] = '🟢 ACTIVE'
            keyboard = keyboard_account(account['phone'])

            if account['phone'] not in accounts.keys():
                client = TelegramClient(StringSession(account['session_string']), api_id=APP_API_ID, api_hash=APP_API_HASH); await client.connect()
                await client.connect()
                if not await client.is_user_authorized():
                    raise

                accounts.setdefault(account['phone'], {})['connect'] = client

            else:
                try:
                    await accounts[account['phone']]['connect'].get_me()
                    if not await accounts[account['phone']]['connect'].is_user_authorized():
                        raise
                
                except:
                    client = TelegramClient(StringSession(account['session_string']), api_id=APP_API_ID, api_hash=APP_API_HASH); await client.connect()
                    await client.connect()
                    if not await client.is_user_authorized():
                        raise

                    accounts.setdefault(account['phone'], {})['connect'] = client

        except:
            accounts.pop(account['phone'], None)
            account['status'] = '🔴 NO VALID'
            keyboard = keyboard_del_account(account['phone'])

        text_account_information = data2text(account, text_account_info)
        await message.answer(text=text_account_information, reply_markup=keyboard)

    await message.answer(text='👥 Need add account?', reply_markup=keyboard_add_account())



@dp.callback_query_handler(text=bt_add_account)
async def callback_add_account(call: types.CallbackQuery):
    await FSM_NewAccount.first()
    await call.message.answer(text='📱 Send PHONE NUMBER (example: 79000000000)', reply_markup=keyboard_cancel())

@dp.message_handler(state=FSM_NewAccount.phone)
async def callback_add_account_phone(message: types.Message, state: FSMContext):
    phone = message.text

    if cursor.execute("SELECT * FROM `accounts` WHERE `phone` = :phone", {'phone': phone}).fetchone() is not None:
        await message.reply('📵 This PHONE NUMBER is already in use, please try another one')
        return False

    try:
        global client; client = TelegramClient(None, api_id=APP_API_ID, api_hash=APP_API_HASH)
        await client.connect()

        send_code = await client.send_code_request(phone)
        phone_code_hash = send_code.phone_code_hash

        await state.update_data(phone=phone)
        await state.update_data(phone_code_hash=phone_code_hash)

        await message.reply('✉️ Send the CODE that sent you the Telegram')
        await FSM_NewAccount.next()
    
    except PhoneNumberInvalidError:
        await message.reply('📵 Invalid PHONE NUMBER, please try again')
    
    except FloodWaitError:
        await message.reply(f'🕓 Too many requests, please wait {FloodWaitError.seconds} seconds')

    except Exception as ex:
        await message.reply(f'{ex}')

@dp.message_handler(state=FSM_NewAccount.code)
async def callback_add_account_code(message: types.Message, state: FSMContext):
    code = message.text

    user_data = await state.get_data()

    await state.update_data(code=code)
    phone = user_data['phone']
    phone_code_hash = user_data['phone_code_hash']

    try:
        global client; await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        
        accounts.setdefault(phone, {})['connect'] = client
        account_get_me = await accounts[phone]['connect'].get_me()

        cursor.execute(f"INSERT INTO `accounts` (`id_telegram`, `phone`, `name`, `surname`, `session_string`) VALUES (:id_telegram, :phone, :name, :surname, :session_string)", {'id_telegram': account_get_me.id, 'phone': phone, 'name': account_get_me.first_name, 'surname': account_get_me.last_name, 'session_string': StringSession.save(client.session)})
        conn.commit()

        await message.answer(text='✅ Account added SUCCESFULLY', reply_markup=keyboard_main())
        await state.finish()


    except PhoneCodeInvalidError:
        await message.reply('❌ Invalid CODE, please try again')

    except PhoneCodeExpiredError:
        await message.reply('❌ Code EXPIRED')
    
    except SessionPasswordNeededError:
        await FSM_NewAccount.next()
        await message.answer(text='🔐 Send cloud PASSWORD with Telegram account', reply_markup=keyboard_main())

    except Exception as ex:
        await message.reply(f'{ex}')

@dp.message_handler(state=FSM_NewAccount.password)
async def callback_add_account_password(message: types.Message, state: FSMContext):
    password = message.text

    user_data = await state.get_data()

    phone = user_data['phone']
    phone_code_hash = user_data['phone_code_hash']
    code = user_data['code']

    try:
        global client; await client.sign_in(password=password)
        
        accounts.setdefault(phone, {})['connect'] = client
        account_get_me = await accounts[phone]['connect'].get_me()

        cursor.execute(f"INSERT INTO `accounts` (`id_telegram`, `phone`, `name`, `surname`, `session_string`) VALUES (:id_telegram, :phone, :name, :surname, :session_string)", {'id_telegram': account_get_me.id, 'phone': phone, 'name': account_get_me.first_name, 'surname': account_get_me.last_name, 'session_string': StringSession.save(client.session)})
        conn.commit()

        await message.answer(text='✅ Account added SUCCESFULLY', reply_markup=keyboard_main())
        await state.finish()


    except PasswordHashInvalidError:
        await message.reply('❌ Password INCORRECT')
    
    except Exception as ex:
        await message.reply(f'{ex}')


@dp.callback_query_handler(Text(startswith=bt_del_account))
async def callback_del_account(call: types.CallbackQuery):
    phone = call.data.replace(bt_del_account, '').strip()

    await bot.edit_message_text(text='🗑 Account DELETED', chat_id=call.message.chat.id, message_id=call.message.message_id)

    accounts.pop(phone, None)

    cursor.execute("DELETE FROM `accounts` WHERE `phone` = :phone", {'phone': phone})
    conn.commit()

    await asyncio.sleep(4)
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


@dp.callback_query_handler(Text(startswith=bt_edit_note))
async def callback_edit_note(call: types.CallbackQuery, state: FSMContext):
    phone = int(call.data.replace(bt_edit_note, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False

    await FSM_Progress.editNote.set()
    await state.update_data(phone=phone)
    await call.message.answer(text='📌 Write a NOTE for this account', reply_markup=keyboard_cancel())

@dp.message_handler(state=FSM_Progress.editNote)
async def message_edit_note(message: types.Message, state: FSMContext):
    note = message.text

    user_data = await state.get_data()
    phone = user_data['phone']

    cursor.execute("UPDATE `accounts` SET `note` = :note WHERE `phone` = :phone", {'phone': phone, 'note': note})
    conn.commit()

    await message.reply(text='✅ Saved', reply_markup=keyboard_main())
    await state.finish()


@dp.callback_query_handler(Text(startswith=bt_edit_message))
async def callback_edit_message(call: types.CallbackQuery, state: FSMContext):
    phone = int(call.data.replace(bt_edit_message, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False

    await FSM_Progress.editMessage.set()
    await state.update_data(phone=phone)
    await call.message.answer(text='✉️ Write a SPAM-MESSAGE for this account', reply_markup=keyboard_cancel())

@dp.message_handler(state=FSM_Progress.editMessage)
async def message_edit_message(message: types.Message, state: FSMContext):
    text_message = message.text

    user_data = await state.get_data()
    phone = user_data['phone']

    cursor.execute("UPDATE `accounts` SET `text_message` = :text_message WHERE `phone` = :phone", {'phone': phone, 'text_message': text_message})
    conn.commit()

    await message.reply(text='✅ Saved', reply_markup=keyboard_main())
    await state.finish()



@dp.callback_query_handler(Text(startswith=bt_list_groups))
async def callback_list_groups(call: types.CallbackQuery):
    phone = int(call.data.replace(bt_list_groups, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False

    arr_groups = await get_groups(phone)

    if not len(arr_groups):
        await call.message.answer(f'LIST GROUP`S\n\n👤 {phone}\n📦 Not a member of a group!')
        return False
    
    file_buffer = BytesIO('\n'.join(map(str, arr_groups)).encode())
    file_buffer.name = f'List_Groups_{phone}.txt'

    await bot.send_document(call.message.chat.id, file_buffer, caption=f'LIST GROUP`S\n\n👤 {phone}\n📦 {len(arr_groups)} groups')



@dp.callback_query_handler(Text(startswith=bt_add_groups))
async def callback_add_groups(call: types.CallbackQuery, state: FSMContext):
    phone = int(call.data.replace(bt_add_groups, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False
    
    await FSM_Progress.addGroups.set()
    await state.update_data(phone=phone)

    await call.message.answer(text='🖊 Write the @domains of the groups you want to join', reply_markup=keyboard_cancel())



@dp.message_handler(state=FSM_Progress.addGroups)
async def message_add_groups(message: types.Message, state: FSMContext):
    arr_groups = message.text.split()

    user_data = await state.get_data()
    phone = user_data['phone']

    await state.finish()

    await message.answer(text=text_main, reply_markup=keyboard_main())

    text_message = '''
JOIN GROUP`S

👤 Account: +:phone:
📦 Total groups received: :count_groups:

✅ Done: :count_done:
❌ Error: :count_error:
'''

    client = accounts[phone]['connect']
    data = {'phone': f'+{phone}', 'count_groups': len(arr_groups), 'count_done': 0, 'count_error': 0}

    entity_message = await message.answer(text=data2text(data, text_message))
    message_id = entity_message.message_id

    for group in arr_groups:
        try:
            group = group.replace('@', '').replace('https', '').replace('http', '').replace(':', '').replace('t.me', '').replace('telegram.com', '').replace('telegram.org', '').replace('joinchat', '').replace('/', '').replace(' ', '').strip()
            
            group = f'@{group}'
            entity = await client.get_entity(str(group))
            
            await client(JoinChannelRequest(entity))
            data['count_done'] += 1
        

        except:
            data['count_error'] += 1
            

        finally:
            await entity_message.edit_text(text=data2text(data, text_message))
            await asyncio.sleep(random.randint(int(config.get('SETTINGS', 'delayJoinMin')), int(config.get('SETTINGS', 'delayJoinMax'))))



@dp.callback_query_handler(Text(startswith=bt_del_groups))
async def callback_del_groups(call: types.CallbackQuery, state: FSMContext):
    phone = int(call.data.replace(bt_del_groups, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False
    
    await FSM_Progress.delGroups.set()
    await state.update_data(phone=phone)

    await call.message.answer(text='🖊 Write the ID`s of the groups you want to delete', reply_markup=keyboard_cancel())



@dp.message_handler(state=FSM_Progress.delGroups)
async def message_del_groups(message: types.Message, state: FSMContext):
    arr_groups = message.text.split()

    user_data = await state.get_data()
    phone = user_data['phone']

    await state.finish()

    await message.answer(text=text_main, reply_markup=keyboard_main())

    text_message = '''
DELETE GROUP`S

👤 Account: +:phone:
📦 Total groups received: :count_groups:

✅ Done: :count_done:
❌ Error: :count_error:
'''

    client = accounts[phone]['connect']
    data = {'phone': f'+{phone}', 'count_groups': len(arr_groups), 'count_done': 0, 'count_error': 0}

    entity_message = await message.answer(text=data2text(data, text_message))
    message_id = entity_message.message_id

    for group in arr_groups:
        try:
            group = group.replace('@', '').replace('-', '').strip()
            
            if group.isdigit():
                group = f'-{group}'
                entity = await client.get_entity(int(group))
            
            else:
                group = f'@{group}'
                entity = await client.get_entity(str(group))
            
            await client(LeaveChannelRequest(entity))
            data['count_done'] += 1
        

        except:
            data['count_error'] += 1
            

        finally:
            await entity_message.edit_text(text=data2text(data, text_message))
            await asyncio.sleep(int(random.randint(config.get('SETTINGS', 'delayLeaveMin')), int(config.get('SETTINGS', 'delayLeaveMax'))))





@dp.callback_query_handler(Text(startswith=bt_start_spam))
async def callbackeyboard_main_spam(call: types.CallbackQuery):
    phone = int(call.data.replace(bt_start_spam, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False
    
    if phone in accounts.keys() and 'work' in accounts[phone].keys() and accounts[phone]['work']:
        await call.answer('❗️ This Account is ALREADY working', show_alert=True)
        return False
    
    elif phone not in accounts.keys():
        await call.answer('❗️ This account is NOT active', show_alert=True)

        cursor.execute("SELECT * FROM `accounts` WHERE `phone` = :phone", {'phone': phone})
        row = cursor.fetchone()
        data = dict(zip([col[0] for col in cursor.description], row)) if row else {}

        data['status'] = '🔴 NO VALID'
        text_account_information = data2text(data, text_account_info)

        await call.message.edit_text(text=data2text(data, text_account_information), reply_markup=keyboard_del_account(phone))
        return False

    accounts[phone]['work'] = loop.create_task(run_spam(call, phone))



@dp.callback_query_handler(Text(startswith=bt_stop_spam))
async def callback_stop_spam(call: types.CallbackQuery):
    phone = int(call.data.replace(bt_stop_spam, ''))

    if not cursor.execute("SELECT * FROM `accounts` WHERE phone = :phone", {'phone': phone}).fetchone():
        await bot.edit_message_text(text='🗑 Account is NOT FOUND in the Database', chat_id=call.message.chat.id, message_id=call.message.message_id)
        await asyncio.sleep(4)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        return False
    
    if phone in accounts.keys() and 'work' in accounts[phone].keys() and accounts[phone]['work']:
        accounts[phone]['work'].cancel()
        del accounts[phone]['work']

        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='🔴 SPAM IS OVER')
    
    else:
        await call.answer('❗️ This Account is NOT working', show_alert=True)
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)






@dp.callback_query_handler(Text(startswith=bt_send, ignore_case=True))
async def delay_send(call: types.CallbackQuery, state: FSMContext):
    min_delay = config.get('SETTINGS', 'delaySendMin')
    max_delay = config.get('SETTINGS', 'delaySendMax')
    await call.message.answer(text=f'✏️ Set the delay interval (in seconds). Currently set values: {min_delay} - {max_delay}', reply_markup=keyboard_cancel())
    await FSM_Settings.send.set()

@dp.message_handler(state=FSM_Settings.send)
async def delay_send_edit(message: types.Message, state: FSMContext):
    msg = re.sub(r"[^0-9-]", '', message.text)
    arr_msg = msg.split('-')

    if len(arr_msg) == 2 and arr_msg[0].isdigit() and arr_msg[1].isdigit():
        min_delay = min(list(map(int, arr_msg)))
        max_delay = max(list(map(int, arr_msg)))

        try:
            config.set('SETTINGS', 'delaySendMin', str(min_delay))
            config.set('SETTINGS', 'delaySendMax', str(max_delay))

            with open('settings.ini', 'w') as configfile:
                config.write(configfile)

            await state.finish()
            await message.answer(text='✅ Saved', reply_markup=keyboard_main())

        except:
            await message.answer(text='⚠️ Error saving, please try again', reply_markup=keyboard_main())

    else:
        await message.answer(f'❗️ Please try again with a different input. Here\'s an example response: 2 - 8')

@dp.callback_query_handler(Text(startswith=bt_cycle, ignore_case=True))
async def delay_cycle(call: types.CallbackQuery, state: FSMContext):
    min_delay = config.get('SETTINGS', 'delayCycleMin')
    max_delay = config.get('SETTINGS', 'delayCycleMax')
    await call.message.answer(text=f'✏️ Set the delay interval (in seconds). Currently set values: {min_delay} - {max_delay}', reply_markup=keyboard_cancel())
    await FSM_Settings.cycle.set()

@dp.message_handler(state=FSM_Settings.cycle)
async def delay_cycle_edit(message: types.Message, state: FSMContext):
    msg = re.sub(r"[^0-9-]", '', message.text)
    arr_msg = msg.split('-')

    if len(arr_msg) == 2 and arr_msg[0].isdigit() and arr_msg[1].isdigit():
        min_delay = min(list(map(int, arr_msg)))
        max_delay = max(list(map(int, arr_msg)))

        try:
            config.set('SETTINGS', 'delayCycleMin', str(min_delay))
            config.set('SETTINGS', 'delayCycleMax', str(max_delay))

            with open('settings.ini', 'w') as configfile:
                config.write(configfile)

            await state.finish()
            await message.answer(text='✅ Saved', reply_markup=keyboard_main())

        except:
            await message.answer(text='⚠️ Error saving, please try again', reply_markup=keyboard_main())

    else:
        await message.answer(f'❗️ Please try again with a different input. Here\'s an example response: 2 - 8')

@dp.callback_query_handler(Text(startswith=bt_join, ignore_case=True))
async def delay_join(call: types.CallbackQuery, state: FSMContext):
    min_delay = config.get('SETTINGS', 'delayJoinMin')
    max_delay = config.get('SETTINGS', 'delayJoinMax')
    await call.message.answer(text=f'✏️ Set the delay interval (in seconds). Currently set values: {min_delay} - {max_delay}', reply_markup=keyboard_cancel())
    await FSM_Settings.join.set()

@dp.message_handler(state=FSM_Settings.join)
async def delay_join_edit(message: types.Message, state: FSMContext):
    msg = re.sub(r"[^0-9-]", '', message.text)
    arr_msg = msg.split('-')

    if len(arr_msg) == 2 and arr_msg[0].isdigit() and arr_msg[1].isdigit():
        min_delay = min(list(map(int, arr_msg)))
        max_delay = max(list(map(int, arr_msg)))

        try:
            config.set('SETTINGS', 'delayJoinMin', str(min_delay))
            config.set('SETTINGS', 'delayJoinMax', str(max_delay))

            with open('settings.ini', 'w') as configfile:
                config.write(configfile)

            await state.finish()
            await message.answer(text='✅ Saved', reply_markup=keyboard_main())

        except:
            await message.answer(text='⚠️ Error saving, please try again', reply_markup=keyboard_main())

    else:
        await message.answer(f'❗️ Please try again with a different input. Here\'s an example response: 2 - 8')

@dp.callback_query_handler(Text(startswith=bt_leave, ignore_case=True))
async def delay_leave(call: types.CallbackQuery, state: FSMContext):
    min_delay = config.get('SETTINGS', 'delayLeaveMin')
    max_delay = config.get('SETTINGS', 'delayLeaveMax')
    await call.message.answer(text=f'✏️ Set the delay interval (in seconds). Currently set values: {min_delay} - {max_delay}', reply_markup=keyboard_cancel())
    await FSM_Settings.leave.set()

@dp.message_handler(state=FSM_Settings.leave)
async def delay_leave_edit(message: types.Message, state: FSMContext):
    msg = re.sub(r"[^0-9-]", '', message.text)
    arr_msg = msg.split('-')

    if len(arr_msg) == 2 and arr_msg[0].isdigit() and arr_msg[1].isdigit():
        min_delay = min(list(map(int, arr_msg)))
        max_delay = max(list(map(int, arr_msg)))

        try:
            config.set('SETTINGS', 'delayLeaveMin', str(min_delay))
            config.set('SETTINGS', 'delayLeaveMax', str(max_delay))

            with open('settings.ini', 'w') as configfile:
                config.write(configfile)

            await state.finish()
            await message.answer(text='✅ Saved', reply_markup=keyboard_main())

        except:
            await message.answer(text='⚠️ Error saving, please try again', reply_markup=keyboard_main())

    else:
        await message.answer(f'❗️ Please try again with a different input. Here\'s an example response: 2 - 8')


# - - - - - [ \DP ] - - - - -





# - - - - - [ RUN ] - - - - -

async def run_spam(call, phone):
    text_spam_message = cursor.execute("SELECT `text_message` FROM `accounts` WHERE `phone` = :phone", {'phone': phone}).fetchone()[0]
    text_message = '''
:type:

👤 Account: +:phone:
📦 Total groups: :count_groups:

✅ Done: :count_done:
❌ Error: :count_error:
'''

    data = {'type': '🟢 SPAM IS STARTED', 'phone': f'+{phone}', 'count_groups': 0, 'count_done': 0, 'count_error': 0}
    entity_message = await call.message.answer(text=data2text(data, text_message), reply_markup=keyboard_stop_spam(phone))
    
    while True:
        try:
            arr_groups = await get_groups(phone)
            data['count_groups'] = len(arr_groups)

        except:
            await asyncio.sleep(60)
            continue

        for group in arr_groups:
            try:
                await accounts[phone]['connect'].send_message(group, text_spam_message) # await accounts[phone]['connect'].send_message(client.get_entity(int(group.replace('-', ''))), text_spam_message)
                data['count_done'] += 1
            
            except Exception as ex:
                data['count_error'] += 1
            
            finally:
                await entity_message.edit_text(text=data2text(data, text_message), reply_markup=keyboard_stop_spam(phone))
                await asyncio.sleep(random.randint(int(config.get('SETTINGS', 'delaySendMin')), int(config.get('SETTINGS', 'delaySendMax'))))

        if len(arr_groups) == 0:
            break
        
        await asyncio.sleep(random.randint(int(config.get('SETTINGS', 'delayCycleMin')), int(config.get('SETTINGS', 'delayCycleMax'))))

    data['type'] = '🔴 SPAM IS OVER'
    await bot.delete_message(chat_id=call.message.chat.id, message_id=entity_message.message_id)
    await call.message.answer(text=data2text(data, text_message))

    accounts[phone]['work'].cancel()
    del accounts[phone]['work']

# - - - - - [ \RUN ] - - - - -





# - - - - - [ ON STARTUP ] - - - - -


async def startup_get_accounts(dp):
    global accounts

    cursor.execute("SELECT * FROM `accounts`")
    rows = cursor.fetchall()
    arr_accounts_db = [dict(zip([col[0] for col in cursor.description], row)) for row in rows] if rows else []

    for account in arr_accounts_db:
        try:
            if account['phone'] not in accounts.keys():
                client = TelegramClient(StringSession(account['session_string']), api_id=APP_API_ID, api_hash=APP_API_HASH)
                await client.connect()

                if not await client.is_user_authorized():
                    raise

                accounts.setdefault(account['phone'], {})['connect'] = client

        except:
            accounts.pop(account['phone'], None)


# - - - - - [ \ON STARTUP ] - - - - -





# - - - - - [ START ] - - - - -

def main():
    executor.start_polling(dp, skip_updates=True, on_startup=startup_get_accounts)

if __name__ == '__main__':
    main()

# - - - - - [ \START ] - - - - -