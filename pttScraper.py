#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import sys
import json
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd


def scraper(board, fileName, numOfPages=1, whichPage=2, data_format='csv'):
	resp = requests.get('https://www.ptt.cc/bbs/'+board+'/index.html')
	resp = enterAgeCheck(resp, board)
	soup = BeautifulSoup(resp.text, 'lxml')
	
	# 如網頁忙線中，隔一秒再連接
	if (soup.title.text.find('Service Temporarily') > -1):
		print '\nService busy...'
		time.sleep(1)
	else:
		print '\nStart scraping...\n'
		# scraping start from given page 'whichPage'
		for page in xrange(whichPage-1):
			try:
				pageUp = soup.select('.btn-group-paging')[0].findAll('a')[1]
				url = pageUp.attrs['href']
				resp = requests.get('https://www.ptt.cc' + url)
				soup = BeautifulSoup(resp.text, 'lxml')
			except Exception as e:
				print e + 'Less pages than given number in %s' %board
				break
		data = []
		# scrape page by page
		for page in xrange(numOfPages):
			print 'Scraping page %d...' %(page + 1)
			
			links = soup.select('.title')
			for link in links:
				try:
					url = link.find('a').attrs['href']
				except:
					continue
				sample_data = linkParser(url)
				if sample_data:
					data.append(sample_data)
				# delay the downloading speed
				time.sleep(0.1)

			try:
				pageUp = soup.select('.btn-group-paging')[0].findAll('a')[1]
				url = pageUp.attrs['href']
				resp = requests.get('https://www.ptt.cc' + url)
				soup = BeautifulSoup(resp.text, 'lxml')
			except:
				print 'Cannot scrape next page. May be the final page.'
				break
			# delay the downloading speed
			time.sleep(0.1)
		
		print 'Done scraping.\n'
		dataStore(data, fileName, format=data_format)


def enterAgeCheck(response, board):
	# 檢查網址是否包含'over18'字串 ,如有則為18禁網站
	if response.url.find('over18') > -1:
		print 'The board is admitted for over 18 only.'
		data_to_load = {
			'from': '/bbs/' + board + '/index.html',
            'yes': 'yes'
		}
		response = requests.post(response.url.split('?')[0], data=data_to_load)
		return response
	else:
		return response


def metaCheck(soup, class_tag, data_name, index, link):
    # 標題列可能被使用者自行刪除
    try:
        data = soup.select(class_tag)[index].text
    except:
        print 'Error in %s with no %s' %(link, data_name)
        data = data_name + '_missed'
    return data


def linkParser(url):
	## Parsing data items from given link
	resp = requests.get('https://www.ptt.cc'+url)
	soup = BeautifulSoup(resp.text, 'lxml')
	#children = [c for c in soup.select('#main-content')[0].children]
	mainContent = soup.select('#main-content')[0]
	
	# Author
	author = metaCheck(mainContent, '.article-meta-value', 'author', 0, url).encode('utf-8')
	# Title
	title = metaCheck(mainContent, '.article-meta-value', 'title', 2, url).encode('utf-8')
	# Date
	date = metaCheck(mainContent, '.article-meta-value', 'date', 3, url)
	
	# Article
	try:
		article = mainContent.text
		article = article.split('\n--')[0]
		article = article.split(date)[1].encode('utf-8')
	except:
		print 'Error in %s with no article.' %url
		return None

	# IP
	try:
		target = u'※ 發信站: 批踢踢實業坊'
		ip = mainContent.find(string=re.compile(target))
		ip = re.search(r'[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*', ip).group()
	except:
		print 'Error in %s with no ip.' %url
		ip = 'ip_missed'
	
	# Messages
	pushNum, booNum, msgNum, msgList = 0, 0, 0, []
	for tag in mainContent.select('.push'):
		try:
			tagContent = [c for c in tag.children]
			msgList.append(tagContent[2].text.encode('utf-8'))
			msgNum += 1
			if tagContent[0].text == u'推':
				pushNum += 1
			elif tagContent[0].text == u'噓':
				booNum += 1
		except:
			continue
	
	sample_data = {'author': author, 'title': title, 'date': date, 'article': article, \
			'messages': msgList, 'numOfMsg': msgNum, 'numOfPush': pushNum, 'numOfBoo': booNum}
	
	return sample_data


def dataStore(data, fileName, format='csv'):
	if format=='csv':
		pd.DataFrame(data).to_csv(fileName+'.csv', index=False)
	elif format=='json':
		with open(fileName+'.json', 'w') as f:
			json.dump(data, f)


if __name__ == "__main__":
	pttName = str(sys.argv[1])
	
	try:
		numOfPages=int(sys.argv[2])
	except:
		numOfPages = 1

	try:
		whichPage=int(sys.argv[3])
	except:
		whichPage = 2
	
	fileName = pttName+'_raw'+datetime.now().strftime('%Y%m%d')
	t0 = time.time()
	scraper(board=pttName, numOfPages=numOfPages, whichPage=whichPage, fileName=fileName)
	print 'Scraping with elapsed time', time.time()-t0, 'seconds.'


