from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from time import sleep

bot = Bot(token='5832598133:AAEDh9o280h2kh122zs_WOTar8uxmPQZBFA')
dp = Dispatcher(bot)

answers = []  # store the answers they have given


### add stuff here


# this is the last line
executor.start_polling(dp)