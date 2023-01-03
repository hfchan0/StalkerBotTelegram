from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from time import sleep
import os
from dotenv import load_dotenv
load_dotenv()
bot_token = os.getenv("token")
print(bot_token)

bot = Bot(token=bot_token)
dp = Dispatcher(bot)

answers = []  # store the answers they have given

### Main Program

# language selection
lang1 = KeyboardButton('English')  
lang2 = KeyboardButton('Other language 🤝')
lang_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(lang1).add(lang2)

# sends welcome message after start
@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
    await message.answer('Hello! Please select your language.\n', reply_markup = lang_kb)
    
# sends help message
@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer('\n')

# options selection: English
en_options1 = KeyboardButton('Psychological support 🧠')
en_options2 = KeyboardButton('Supplies: food, medicine, hormones, ... 🍇')
en_options3 = KeyboardButton('Border crossing 🏇')
en_options4 = KeyboardButton('Other help 📚')
en_options_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(en_options1).add(en_options2).add(en_options3).add(en_options4)

#### selecting what you need
@dp.message_handler(regexp='English')
async def english(message: types.Message):
    answers.append(message.text)
    await message.answer('What do you need?', reply_markup = en_options_kb)
    
### End of Main Program

# this is the last line
executor.start_polling(dp)