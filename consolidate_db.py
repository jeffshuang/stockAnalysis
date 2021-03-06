import datetime
import hashlib
import pprint

from pymongo.errors import BulkWriteError

import pytz
from modules.helpers import customHash
from modules.hyperparameters import constants
from dateutil.parser import parse


def get_ticker(message):
    words = message.split()
    tickers = []
    for w in words:
        if w[0] == '$' and w[1:].isupper():
            if (' ' in w[1:] or not w[1:].isalpha()):
                continue
            tickers.append(w[1:])
    if len(tickers) != 1:
        return None
    return ticker[0]


def well_formatted(ticker):
    if ticker is None:
        return True
    if ' ' in ticker:
        return False
    if not ticker.isalpha():
        return False
    return True


def clean(ticker):
    clean_ticker = ''
    for c in ticker:
        if c.isalpha():
            clean_ticker += c
        else:
            break
    return clean_ticker


def transfer(origin, destination, extract_ticker=False):
    all_tweets = origin.find({}, no_cursor_timeout=True)
    count = 0
    to_write = []
    for tweet in all_tweets:
        # if (count == 10000):
        #     break
        # if count % 10000 == 0:
        #     print('Processed %d tweets' % count)
        #     try:
        #         destination.insert_many(to_write, ordered=False)
        #     except BulkWriteError as bwe:
        #         pprint.pprint(bwe.details)
        #         pass
        #     to_write = []

        w = {}
        if extract_ticker:
            w['symbol'] = get_ticker(tweet['messageText'])
        else:
            w['symbol'] = tweet['symbol']
        
        w['_id'] = customHash(tweet['messageText'] + tweet['time'] + tweet['user'])
        w['user'] = tweet['user']
        w['time'] = parse(tweet['time'])
        w['isBull'] = tweet['isBull']
        w['likeCount'] = tweet['likeCount']
        w['commentCount'] = tweet['commentCount']
        w['messageText'] = tweet['messageText']
        # print(w)
        # print(tweet['_id'])
        try:
            destination.insert_one(w)
        except Exception as e:
            print(count)
            print(str(e))
        
        origin.delete_one({'_id': tweet['_id']})
        count += 1


def transfer_and_delete(origin, destination, extract_ticker=False):
    batch = origin.find({}, no_cursor_timeout=True, limit=100000)
    count = 1
    while batch.count() > 0:
        to_write = []
        to_delete = []
        for tweet in batch:
            count += 1
            if count % 1000 == 0:
                print('Processed %d tweets' % count)
            to_delete.append(tweet['_id'])
            w = {}
            if extract_ticker:
                w['symbol'] = get_ticker(tweet['messageText'])
            else:
                w['symbol'] = tweet['symbol']
            w['_id'] = customHash(tweet['messageText']+tweet['time']+tweet['user'])
            w['user'] = tweet['user']
            w['time'] = datetime.datetime.strptime(tweet['time'], '%Y-%m-%d %H:%M:%S')
            etz = pytz.timezone('US/Eastern')
            etz.localize(w['time'])
            w['isBull'] = tweet['isBull']
            w['likeCount'] = tweet['likeCount']
            w['commentCount'] = tweet['commentCount']
            w['messageText'] = tweet['messageText']
            to_write.append(w)
        try:
            destination.insert_many(to_write, ordered=False)
        except BulkWriteError as bwe:
            print(bwe.details)
        origin.delete_many({'_id': {'$in':to_delete}})
        batch = origin.find({}, no_cursor_timeout=True, limit=100000)


user_tweets_db = constants['db_user_client'].get_database('user_data_db').user_info
stock_tweets_db = constants['stocktweets_client'].get_database('stocks_data_db').stock_tweets
consolidated_tweets_db = constants['stocktweets_client'].get_database('tweets_db').tweets
clean_db = constants['stocktweets_client'].get_database('tweets_db').clean_tweets

"""
transfer_and_delete(stock_tweets_db, consolidated_tweets_db) 
transfer_and_delete(user_tweets_db, consolidated_tweets_db, True)
"""
transfer(stock_tweets_db, consolidated_tweets_db)
