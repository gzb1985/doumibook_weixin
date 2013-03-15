#!/bin/env python
# -*- coding: utf-8 -*- 
import os
import hashlib
import urllib
import urllib2
import json
import re

import xml.etree.ElementTree as ET

from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Response
from flask import jsonify

from util import deployed_on_sae
from private_const import *

app = Flask(__name__)
app.debug = True
app.secret_key = app_secret_key

@app.route('/')
def home():
	return render_template('index.html')

#微信消息服务器接入
@app.route('/weixin', methods=['GET'])
def weixin_verify():
    signature = request.args.get('signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    echostr = request.args.get('echostr')
    
    token = 'doumi' #注意要与微信公众帐号平台上填写一致
    tmplist = [token, timestamp, nonce]
    tmplist.sort()
    tmpstr = ''.join(tmplist)
    hashstr = hashlib.sha1(tmpstr).hexdigest()

    if hashstr == signature:
        return echostr
    return 'Error' + echostr

bookurlbase = 'http://api.douban.com/v2/book/search'

def parse_msg(rawmsgstr):
    root = ET.fromstring(rawmsgstr)
    msg = {}
    for child in root:
        msg[child.tag] = child.text
    return msg

def search_book(q):
    params = {'q': q.encode('utf-8'), 'apikey': DOUBAN_APIKEY, 'count': 3}
    url = bookurlbase + '?' + urllib.urlencode(params)
    resp = urllib2.urlopen(url)
    r = json.loads(resp.read())
    books = r['books']
    return books

def book_info(books):
    info = ''.join((''.join(book['author']) + ': ' + book['title'] + '\n') for book in books)
    return info

def response_text_msg(recvmsg, content):
    textTpl = """<xml>
            <ToUserName><![CDATA[%s]]></ToUserName>
            <FromUserName><![CDATA[%s]]></FromUserName>
            <CreateTime>%s</CreateTime>
            <MsgType><![CDATA[%s]]></MsgType>
            <Content><![CDATA[%s]]></Content>
            <FuncFlag>0</FuncFlag>
            </xml>"""
    echostr = textTpl % (recvmsg['FromUserName'], recvmsg['ToUserName'], recvmsg['CreateTime'], recvmsg['MsgType'], content)
    return echostr

def make_item(book, itemindex):
    itemTpl = u"""
    <item>
        <Title><![CDATA[%s\t%s分\n%s\n%s\t%s]]></Title>
        <Description><![CDATA[]]></Description>
        <PicUrl><![CDATA[%s]]></PicUrl>
        <Url><![CDATA[%s]]></Url>
    </item>"""
    picUrl = book['images']['large'] if itemindex == 1 else book['images']['small']
    url = re.sub('http://douban','http://m.douban', book['alt'])
    item = itemTpl % (book['title'], book['rating']['average'], 
        ','.join(book['author']), book['publisher'], book['price'], picUrl, url)
    return item

def make_single_item(book):
    itemTpl = u"""
    <item>
        <Title><![CDATA[%s\t%s分]]></Title>
        <Description><![CDATA[%s\n%s\t%s]]></Description>
        <PicUrl><![CDATA[%s]]></PicUrl>
        <Url><![CDATA[%s]]></Url>
    </item>"""
    picUrl = book['images']['large']
    item = itemTpl % (book['title'], book['rating']['average'], 
        ','.join(book['author']), book['publisher'], book['price'], picUrl, book['alt'])
    return item

def response_news_msg(recvmsg, books):
    msgStartTpl = """<xml>
    <ToUserName><![CDATA[%s]]></ToUserName>
    <FromUserName><![CDATA[%s]]></FromUserName>
    <CreateTime>%s</CreateTime>
    <MsgType><![CDATA[news]]></MsgType>
    <Content><![CDATA[]]></Content>
    <ArticleCount>%d</ArticleCount>
    <Articles>
    """

    msgEnd = """
    </Articles>
    <FuncFlag>1</FuncFlag>
    </xml>"""
    msgStart = msgStartTpl % (recvmsg['FromUserName'], recvmsg['ToUserName'], recvmsg['CreateTime'], len(books))
    msg = msgStart
    if len(books) == 1:
        msg += make_single_item(books[0])
    else:
        for i, book in enumerate(books):
            msg += make_item(book, i+1)
    msg += msgEnd
    return msg

#来自微信的消息推送
@app.route('/weixin', methods=['POST'])
def weixin_msg():
    data = request.data
    msg = parse_msg(data)
    if msg.has_key('Content'):
        q = msg['Content']
        books = search_book(q)
        rmsg = response_news_msg(msg, books)
        return rmsg
    return 'error'


if __name__ == '__main__':
    app.run()
