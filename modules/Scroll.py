import time
import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup
from dateutil.parser import parse
from .messageExtract import findDateTime
from iexfinance.stocks import get_historical_intraday
from .helpers import analyzedSymbolAlready
from .helpers import addToFailedList
from .fileIO import *


# ------------------------------------------------------------------------
# ----------------------------- Variables --------------------------------
# ------------------------------------------------------------------------


priceAttr = 'st_1NGO3lX'
messageStreamAttr = 'st_2o0zabc'
messagesCountAttr = 'st__tZJhLh'
SCROLL_PAUSE_TIME = 2


# ------------------------------------------------------------------------
# ----------------------------- Functions --------------------------------
# ------------------------------------------------------------------------


def findLastTime(messages):
	lastMessage = messages[len(messages) - 1].text
	t = lastMessage.split('\n')
	if (t[0] == "Bearish" or t[0] == "Bullish"):
		dateTime = findDateTime(t[2])
		return dateTime
	else:
		dateTime = findDateTime(t[1])
		return dateTime


def isStockPage(driver):
	messageCount = driver.find_elements_by_class_name(messagesCountAttr)
	analyzingStock = False
	if (len(messageCount) == 0):
		analyzingStock = True
		price = driver.find_elements_by_class_name(priceAttr)
	return analyzingStock


def pageExists(driver):
	html = driver.page_source
	soup = BeautifulSoup(html, 'html.parser')
	messages = soup.find_all('div', attrs={'class': messageStreamAttr})

	# page Doesnt exist
	currentCount = len(messages)
	if (currentCount == 0):
		return False

	return True


# Scroll for # days
def scrollFor(name, days, driver, progressive):
	dateTime = datetime.datetime.now()
	folderPath = dateTime.strftime("stocksResults/%m-%d-%y/")
	oldTime = dateTime - datetime.timedelta(days)
	oldTime = datetime.datetime(oldTime.year, oldTime.month, oldTime.day, 9, 30)
	failPath = "failedList.csv"

	# Handles message Timeout exception in the webdriver.py
	try:
		last_height = driver.execute_script("return document.body.scrollHeight")
	except:
		addToFailedList(failPath, dateTime, name)
		return False

	price = driver.find_elements_by_class_name(priceAttr)
	analyzingStock = isStockPage(driver)

	if (pageExists(driver) == False or (len(price) == 0 and analyzingStock)):
		print("Doesn't Exist")
		return False

	count = 1
	modCheck = 1
	analyzedAlready = analyzedSymbolAlready(name, folderPath)
	if (analyzedAlready and analyzingStock and progressive):
		filePath = folderPath + name + '.csv'
		stockRead = readMultiList(filePath)
		if (len(stockRead) == 0):
			pass
		else:
			oldTime = parse(stockRead[0][2])

	firstCheckForStock = False #Must scroll certain amount before checking...more effecient scrolling
	countForCheck = 0
	frequencies = readMultiList("stockFrequency.csv")
	numbers = -1
	for f in frequencies:
		if (f[0] == name):
			numbers = int(f[1])

	# Find number of scrolls to make based on average and time of day it is
	# If it is a stock that has 0 scrolls and it is before, shouldn't even check till later
	# worry about that later though
	messagesPerDay = numbers / 30
	numberScrolls = int(messagesPerDay / 40)

	while(True):
		new_height = driver.execute_script("return document.body.scrollHeight")
		time.sleep(SCROLL_PAUSE_TIME)

		if (analyzingStock):
			if (firstCheckForStock == False and numberScrolls > 0):
				# time.sleep(SCROLL_PAUSE_TIME)
				driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
				new_height = driver.execute_script("return document.body.scrollHeight")
				last_height = new_height

				print(countForCheck, '/', numberScrolls)

				if (countForCheck == numberScrolls):
					firstCheckForStock = True
				else:
					countForCheck += 1
				continue

		if (count % modCheck == 0):
			modCheck += 1
			if (analyzingStock == False):
				for i in range(3):
					time.sleep(SCROLL_PAUSE_TIME)
					driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
					new_height = driver.execute_script("return document.body.scrollHeight")

			time.sleep(SCROLL_PAUSE_TIME)
			driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
			new_height = driver.execute_script("return document.body.scrollHeight")
			messages = driver.find_elements_by_class_name(messageStreamAttr)

			if (len(messages) == 0):
				print("Strange Error")
				return False

			dateTime = findLastTime(messages)

			print(name, dateTime)
			if (analyzingStock == False and new_height == last_height):
				break

		last_height = new_height
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
		count += 1

		# TODO: Need to fix for later (temporary fix)
		if (dateTime == None or oldTime == None):
			print("How does this happen")
			return False

		if (dateTime < oldTime):
			break

	print("Finished Reading", name)
	return True
