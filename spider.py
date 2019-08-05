#coding:utf-8
import threadpool
import threading

import csv

import chardet
import requests
import time
import execjs
from lxml import etree
import random
from urllib import parse
import re
import os
import json
import urllib

lock = threading.Lock()


reqNum = 0

def retry(count=1):
    def dec(f):
        def ff(*args, **kwargs):
            ex = None
            for i in range(count):
                try:
                    ans = f(*args, **kwargs)
                    return ans
                except Exception as e:
                    ex = e
            raise ex

        return ff

    return dec

def log(text):
    def decorator(func):
        def wrapper(*args, **kw):
            print('%s %s():' % (text, func.__name__))
            return func(*args, **kw)

        return wrapper

    return decorator

with open('getcookie.js','r',encoding='utf-8') as f:
    js1 = f.read()
    ecjs = execjs.compile(js1)

csvFile = open("data.csv",mode="w",encoding="gbk",newline="")
csvWriter = csv.writer(csvFile)

class SpiderMain(object):
    def __init__(self,tableId,tableView,curstart):
        self.tableView = tableView
        #参数
        self.F82S = ''
        self.F82T = ''
        self.F82T_true = ''
        self.JSESSIONID = ''
        self.meta = ''
        self.url = 'http://app1.sfda.gov.cn/datasearchcnda/face3/base.jsp?tableId=25&tableName=TABLE25&title=%B9%FA%B2%FA%D2%A9%C6%B7&bcId=152904713761213296322795806604'
        self.url_list = 'http://app1.sfda.gov.cn/datasearchcnda/face3/search.jsp'
        #请求头
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache - Control": "max - age = 0",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "app1.sfda.gov.cn",
            "Referer": "http://app1.sfda.gov.cn/datasearchcnda/face3/base.jsp?tableId=25&tableName=TABLE25&title=%B9%FA%B2%FA%D2%A9%C6%B7&bcId=152904713761213296322795806604",
            "Upgrade - Insecure - Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
        }
        #请求cookie
        self.cookies = {
            'FSSBBIl1UgzbN7N82S':'',
            'FSSBBIl1UgzbN7N82T':'',
            'JSESSIONID':''
        }
        #列表页请求参数
        self.data = {
            'tableId':tableId,
            'curstart':'{}'.format(curstart),
            'tableView':  parse.quote(tableView,encoding='gbk') ,   #'%E4%BA%92%E8%81%94%E7%BD%91%E8%8D%AF%E5%93%81%E4%BF%A1%E6%81%AF%E6%9C%8D%E5%8A%A1',
        }

    @retry(20)
    def postApi(self,url):
        global reqNum
        reqNum += 1
        # 请求模块执行POST请求,response为返回对象

        try:
            response = requests.post(url,headers=self.headers, cookies=self.cookies, data=self.data, timeout=10)
        except requests.exceptions.ConnectTimeout:
            raise Exception


        # 从请求对象中拿到相应内容解码成utf-8 格式
        html = response.content.decode("utf-8")
        return html

    @retry(10)
    def loadPage(self,url, srb=False,notCookie=False):
        global reqNum
        reqNum += 1
        # 请求模块执行POST请求,response为返回对象
        if notCookie:
            response = requests.get(url, headers=self.headers, timeout=10)
        else:
            response = requests.get(url, headers=self.headers, cookies=self.cookies, timeout=10)
        
        if srb:
            return response
        # 从请求对象中拿到相应内容解码成utf-8 格式
        html = response.text
        return html

    def getCookie(self):
        rsq =self.loadPage(self.url,srb=True,notCookie=True)
        rsq.close()
        # print(rsq.cookies)
        #第一次请求得到假的f82s,f82t,和metacontent
        self.F82S = rsq.cookies['FSSBBIl1UgzbN7N82S']
        self.F82T = rsq.cookies['FSSBBIl1UgzbN7N82T']
        rsqHtml = etree.HTML(rsq.text)
        self.meta = rsqHtml.xpath('//*[@id="9DhefwqGPrzGxEp9hPaoag"]/@content')[0]
        self.F82T_true = ecjs.call("getcookie", self.meta,self.F82T)
        self.cookies['FSSBBIl1UgzbN7N82S'] = self.F82S
        self.cookies['FSSBBIl1UgzbN7N82T'] = self.F82T_true
        # rsq = requests.get(self.url, headers=self.headers,cookies = self.cookies)
        # print(rsq.cookies)
        # try:
            # self.JSESSIONID = rsq.cookies['JSESSIONID']
            # self.cookies['JSESSIONID'] = self.JSESSIONID
        # except Exception as e:
        #     print(e)
        #     pass



    def getlist(self,totalData = []):
        rsqlist = self.postApi(self.url_list)
        rsqlistHtml = etree.HTML(rsqlist)
        # print(rsqlist.cookies)
        lists = rsqlistHtml.xpath('//a[contains(@href,"javascript:commitForECMA")]')
        if len(lists) == 0:
            self.getCookie()
            self.getlist(totalData)
            return
        ind = -1
        for list in lists:
            ind += 1
            if ind < len(totalData):
                continue
            name = list.xpath('./text()')[0]
            url = list.xpath('./@href')[0]
            url = "http://app1.sfda.gov.cn/datasearchcnda/face3/" + url[url.index('content.jsp?'):url.index("',null")]
            try:
                dataList = self.parser(url)
            except:
                self.getCookie()
                self.getlist(totalData)
                return
            totalData.append(dataList)
        print(len(totalData))
        csvWriter.writerows(totalData)
    def parser(self,url):
        url = parse.quote(url, safe='/:?=&', encoding='gbk')
        # print(name)
        # print(url)
        content = self.loadPage(url)
        contentHtml = etree.HTML(content)
        try:
            contentList = contentHtml.xpath('//tr')
        except:
            raise Exception
        listcontent = ''
        dataList = []
        for i in range(1, len(contentList) - 1):
            contentList[i].xpath('./tr/text()')
            value_ls = contentList[i].xpath("./td")
            value1 = value_ls[0].xpath('string(.)')
            value2 = value_ls[1].xpath('string(.)')
            listcontent = listcontent + str(value1) + ':' + str(value2) + '||'
            dataList.append(str(value2).encode("gbk", "ignore").decode("gbk"))
        if len(dataList) == 0:
            raise Exception
        return dataList

def Main(page):
    print("page",page)
    try:
        spider = SpiderMain(25, '国产药品', page)
        # lock.acquire()
        spider.getCookie()
        # lock.release()
        spider.getlist(totalData=[])
    except Exception as e:
        print(e)
        with open("err.txt",mode="a") as f:
            f.write('{}\n'.format(page))

    finally:
        del spider

if __name__ == '__main__':
    text =  open("err.txt",mode="r").read()
    params = text.split("\n")
    pool = threadpool.ThreadPool(1)
    tasks = threadpool.makeRequests(Main, params)
    [pool.putRequest(task) for task in tasks]
    pool.wait()
    csvFile.close()
