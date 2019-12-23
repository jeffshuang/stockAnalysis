import datetime
import time
from .helpers import (convertToEST,
                      customHash,
                      endDriver,
                      getActualAllStocks,
                      findWeight,
                      findJoinDate,
                      getAllStocks)
from .hyperparameters import constants
from .stockPriceAPI import (findCloseOpen,
                            inTradingDay,
                            getUpdatedCloseOpen)
from .stockAnalysis import getTopStocks
from .userAnalysis import getAllUserInfo
from random import shuffle


def findBadMessages():
    analyzedUsersDB = constants['db_user_client'].get_database('user_data_db')
    userAccuracy = analyzedUsersDB.user_accuracy_v2
    # allAccs = userAccuracy.find()
    # mappedTweets = list(map(lambda doc: [doc['_id'], doc['1']['returnUnique']['bull']], allAccs))
    # mappedTweets.sort(key=lambda x: x[1], reverse=False)

    # for x in mappedTweets[:30]:
    #     print(x[0], x[1])

    # return
    # allAccs = userAccuracy.find({'perStock.NAKD': { '$exists': True }})
    # mappedTweets = list(map(lambda doc: [doc['_id'], doc['perStock']['NAKD']['1']['returnCloseOpen']['bull'] 
    #                                      + doc['perStock']['NAKD']['1']['returnCloseOpen']['bear']], allAccs))
    # mappedTweets.sort(key=lambda x: x[1], reverse=True)
    # print(len(mappedTweets))
    # shuffle(mappedTweets)
    # for x in mappedTweets:
    #     user = x[0]
    #     userAccuracy.delete_one({'_id': user})
    #     result = getAllUserInfo(user)
    #     print(user, result['accuracyUnique'], result['totalReturnUnique'])
    # return

    user = 'mbarelorenzo'
    # userAccuracy.delete_one({'_id': user})
    userInfo = getAllUserInfo(user)
    perStock = list(userInfo['perStock'].keys())
    print(perStock)
    res = {}
    s1 = 0
    print(userInfo['1']['returnCloseOpen']['bear'])
    for s in perStock:
        res[s] = userInfo['perStock'][s]['1']['returnCloseOpen']['bear']
        s1 += userInfo['perStock'][s]['1']['returnCloseOpen']['bear']
    print(s1)
    bestParams = list(res.items())
    bestParams.sort(key=lambda x: x[1], reverse=False)
    for x in bestParams:
        print(x)
    
