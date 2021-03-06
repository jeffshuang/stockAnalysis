import datetime
import math
from multiprocessing import current_process

import requests

from .hyperparameters import constants


# ------------------------------------------------------------------------
# ----------------------------- Variables --------------------------------
# ------------------------------------------------------------------------


# Invalid symbols so they aren't check again
invalidSymbols = []
currHistorical = []
currSymbol = ""
currDateTimeStr = ""


# ------------------------------------------------------------------------
# ----------------------------- Functions --------------------------------
# ------------------------------------------------------------------------


# Find close open for date. Anytime before 4pm is
def findCloseOpen(symbol, time):
    db = constants['db_client'].get_database('stocks_data_db').updated_close_open
    dayIncrement = datetime.timedelta(days=1)
    nextDay = None
    count = 0

    # If saturday, sunday or holiday, find first trading day to start from time
    testDay = db.find_one({'_id': 'AAPL ' + time.strftime("%Y-%m-%d")})
    while (testDay is None and count != 10):
        time = datetime.datetime(time.year, time.month, time.day)
        time += dayIncrement
        testDay = db.find_one({'_id': 'AAPL ' + time.strftime("%Y-%m-%d")})
        count += 1

    # Find first day if tweeted after 4pm
    # If 4:00 on Wed, first day is Thursday
    # If 4:00 on Friday, first day is Monday
    timeDiff = time - datetime.datetime(time.year, time.month, time.day)
    if (timeDiff.total_seconds() >= (16 * 60 * 60)):
        time += dayIncrement
        testDay = db.find_one({'_id': 'AAPL ' + time.strftime("%Y-%m-%d")})
        while (testDay is None and count != 10):
            time += dayIncrement
            testDay = db.find_one({'_id': 'AAPL ' + time.strftime("%Y-%m-%d")})
            count += 1

    # Find next day based on the picked first day
    nextDay = time + dayIncrement
    testDay = db.find_one({'_id': 'AAPL ' + nextDay.strftime("%Y-%m-%d")})
    while (testDay is None and count != 10):
        nextDay += dayIncrement
        testDay = db.find_one({'_id': 'AAPL ' + nextDay.strftime("%Y-%m-%d")})
        count += 1

    if (count >= 10):
        return None

    start = db.find_one({'_id': symbol + ' ' + time.strftime("%Y-%m-%d")})
    end = db.find_one({'_id': symbol + ' ' + nextDay.strftime("%Y-%m-%d")})

    # If either start or end are 0, don't allow it (fixes TTNP)
    if (end is None) or (start is None) or (end['open'] == 0) or (start['close'] == 0):
        return None
    else:
        closePrice = start['close']
        openPrice = end['open']
        return (closePrice, openPrice, round(((openPrice - closePrice) / closePrice) * 100, 3))


# Close open averaged between 2 sources
def averagedOpenClose(symbol, date):
    updatedOpenClose = getUpdatedCloseOpen(symbol, date)
    ogOpenClose = closeToOpen(symbol, date)

    if (updatedOpenClose is None and ogOpenClose is None):
        return None
    elif (updatedOpenClose is None):
        return ogOpenClose
    elif (ogOpenClose is None):
        return updatedOpenClose
    else:
        closePrice = (updatedOpenClose[0] + ogOpenClose[0]) / 2.0
        openPrice = (updatedOpenClose[1] + ogOpenClose[1]) / 2.0
        return (closePrice, openPrice, round(((openPrice - closePrice) / closePrice) * 100, 3))


def updateAllCloseOpen(stocks, dates, replace=False):
    for symbol in stocks:
        print(symbol)
        for date in dates:
            dateString = date.strftime("%Y-%m-%d")
            idString = symbol + ' ' + dateString
            db = constants['db_client'].get_database('stocks_data_db').updated_close_open
            found = db.find_one({'_id': idString})
            if (found is None or replace):
                result = updatedCloseOpen(symbol, date)
                if (len(result) == 0):
                    continue
                print(result)
                if (found is not None):
                    db.delete_one({'_id': result['_id']})
                db.insert_one(result)
            else:
                print('found', found)


def updatedCloseOpen(symbol, date):
    dateString = date.strftime("%Y%m%d")
    baseURL = "https://cloud.iexapis.com/stable/stock/" + symbol + "/chart/date/"
    restURL = "?chartByDay=True&token=sk_63da34a91b164aeb943b44a8c5861e91"
    URL = baseURL + dateString + restURL
    r = requests.get(url=URL)
    data = r.json()
    if (len(data) == 0):
        return {}
    data = data[0]
    _id = symbol + ' ' + data['date']
    result = {'_id': _id, 'open': data['open'], 'close': data['close']}
    return result


def getUpdatedCloseOpen(symbol, date):
    exceptions = [datetime.datetime(2019, 11, 27)]
    db = constants['db_client'].get_database('stocks_data_db').updated_close_open
    days_in_future = datetime.timedelta(days=1)
    future_date = date + days_in_future
    if (future_date.weekday() > 4):
        next_weekday = datetime.timedelta(days=7 - future_date.weekday())
        future_date += next_weekday

    # Edge Case
    if (date.day == 27 and date.month == 11):
        future_date = date + datetime.timedelta(days=2)

    if (date.day == 30 and date.month == 8):
        future_date = date + datetime.timedelta(days=4)

    start = db.find_one({'_id': symbol + ' ' + date.strftime("%Y-%m-%d")})
    end = db.find_one({'_id': symbol + ' ' + future_date.strftime("%Y-%m-%d")})

    if (end is None) or (start is None) or start == 0 or end == 0:
        print(start, end)
        return None
    else:
        closePrice = start['close']
        openPrice = end['open']
        return (closePrice, openPrice, round(((openPrice - closePrice) / closePrice) * 100, 3))


def inTradingDay(date):
    market_open = datetime.datetime(date.year, date.month, date.day, 9, 30)
    market_close = datetime.datetime(date.year, date.month, date.day, 16, 0)
    day = date.weekday()

    if (date < market_open or date >= market_close or day == 5 or day == 6):
        return False
    return True


def closeToOpen(ticker, time, days=1):
    days_in_future = datetime.timedelta(days=days) 
    future_date = time+days_in_future
    if future_date.weekday() > 4:
        next_weekday = datetime.timedelta(days=7-future_date.weekday())
        future_date += next_weekday
    start = getPriceAtEndOfDay(ticker, time)
    end = getPriceAtBeginningOfDay(ticker, future_date)
    if (end is None) or (start is None) or start == 0 or end == 0:
        return None
    else:
        return (start, end, round(((end-start)/start) * 100, 3))


def getPrice(ticker, time):
    # time should be in datetime.datetime format
    market_open = datetime.datetime(time.year, time.month, time.day, 9, 30)
    market_close = datetime.datetime(time.year, time.month, time.day, 16, 0)
    if time >= market_open and time <= market_close:
        rounded_minute = 5 * round((float(time.minute) + float(time.second)/60)/5)
        minute_adjustment = datetime.timedelta(minutes=rounded_minute-time.minute)
        adj_time = time + minute_adjustment
        adj_time = adj_time.replace(second=0, microsecond=0)
        query_time_s = adj_time.strftime('%Y-%m-%d %H:%M:%S')

    if time > market_close:
        tomorrow = time + datetime.timedelta(days=1)
        next_opening = tomorrow.replace(hour=9, minute=35, second=0)
        query_time_s = next_opening.strftime('%Y-%m-%d %H:%M:%S')

    if time < market_open:
        query_time_s = market_open.strftime('%Y-%m-%d %H:%M:%S')

    query_id = ticker+query_time_s
    stock_price_db = constants['db_client'].get_database('stocks_data_db').stock_data
    price_data = stock_price_db.find_one({'_id': query_id})
    if price_data is None:
        # print('Date out of range or stock not tracked')
        return None
    return price_data['price']


def getPriceAtEndOfDay(ticker, time):
    market_close = datetime.datetime(time.year, time.month, time.day, 15, 50)
    return getPrice(ticker, market_close)


def getPriceAtBeginningOfDay(ticker, time):
    market_open = datetime.datetime(time.year, time.month, time.day, 9, 40)
    return getPrice(ticker, market_open)


# Transfer non labeled tweets to new database (about 50% are unlabled)
def transferNonLabeled(stocks):
    unlabledDB = constants['db_user_client'].get_database('tweets').tweets_unlabeled
    tweetsDB = constants['stocktweets_client'].get_database('tweets_db').tweets

    for s in stocks:
        tweets = tweetsDB.find({'$and': [{'symbol': s}, {'isBull': None}]})
        mappedTweets = list(map(lambda doc: doc, tweets))
        mappedTweets.sort(key=lambda x: x['time'], reverse=True)
        count = 0
        realCount = 0
        print(s, len(mappedTweets))
        for t in mappedTweets:
            count += 1
            # print(t)
            try:
                unlabledDB.insert_one(t)
                realCount += 1
            except:
                pass
            tweetsDB.delete_one({'_id': t['_id']})
            if (count % 100 == 0):
                print(s, count, len(mappedTweets))
        print(s, realCount, count)
