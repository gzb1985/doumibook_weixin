#!/bin/env python
# -*- coding: utf-8 -*- 
import hashlib, urllib, urllib2, re
import xml.etree.ElementTree as ET
from flask import Flask, request, render_template
from util import deployed_on_sae
from private_const import APP_SECRET_KEY, DOUBAN_APIKEY

app = Flask(__name__)
app.debug = True
app.secret_key = APP_SECRET_KEY

#homepage just for fun
@app.route('/')
def home():
    return render_template('index.html')

#公众号消息服务器网址接入验证
#需要在公众帐号管理台手动提交, 验证后方可接收微信服务器的消息推送
@app.route('/weixin', methods=['GET'])
def weixin_access_verify():
    echostr = request.args.get('echostr')
    if verification(request) and echostr is not None:
        return echostr
    return 'access verification fail'

#来自微信服务器的消息推送
@app.route('/weixin', methods=['POST'])
def weixin_msg():
    if verification(request):
        data = request.data
        msg = parse_msg(data)
        if msg.has_key('Content'):
            q = msg['Content']
            books = search_book(q)
            rmsg = response_news_msg(msg, books)
            return rmsg
    return 'message processing fail'

#接入和消息推送都需要做校验
def verification(request):
    signature = request.args.get('signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')

    token = 'doumi' #注意要与微信公众帐号平台上填写一致
    tmplist = [token, timestamp, nonce]
    tmplist.sort()
    tmpstr = ''.join(tmplist)
    hashstr = hashlib.sha1(tmpstr).hexdigest()

    if hashstr == signature:
        return True
    return False

#将消息解析为dict
def parse_msg(rawmsgstr):
    root = ET.fromstring(rawmsgstr)
    msg = {}
    for child in root:
        msg[child.tag] = child.text
    return msg

#访问豆瓣API获取书籍数据
BOOK_URL_BASE = 'http://api.douban.com/v2/book/search'
def search_book(q):
    params = {'q': q.encode('utf-8'), 'apikey': DOUBAN_APIKEY, 'count': 3}
    url = BOOK_URL_BASE + '?' + urllib.urlencode(params)
    resp = urllib2.urlopen(url)
    r = json.loads(resp.read())
    books = r['books']
    return books


NEWS_MSG_HEADER_TPL = \
u"""
<xml>
<ToUserName><![CDATA[%s]]></ToUserName>
<FromUserName><![CDATA[%s]]></FromUserName>
<CreateTime>%s</CreateTime>
<MsgType><![CDATA[news]]></MsgType>
<Content><![CDATA[]]></Content>
<ArticleCount>%d</ArticleCount>
<Articles>
"""

NEWS_MSG_TAIL = \
u"""
</Articles>
<FuncFlag>1</FuncFlag>
</xml>
"""

#消息回复，采用news图文消息格式
def response_news_msg(recvmsg, books):
    msgHeader = NEWS_MSG_HEADER_TPL % (recvmsg['FromUserName'], recvmsg['ToUserName'], 
        recvmsg['CreateTime'], len(books))
    msg = ''
    msg += msgHeader
    msg += make_articles(books)
    msg += NEWS_MSG_TAIL
    return msg

def make_articles(books):
    msg = ''
    if len(books) == 1:
        msg += make_single_item(books[0])
    else:
        for i, book in enumerate(books):
            msg += make_item(book, i+1)
    return msg


NEWS_MSG_ITEM_TPL = \
u"""
<item>
<Title><![CDATA[%s]]></Title>
<Description><![CDATA[%s]]></Description>
<PicUrl><![CDATA[%s]]></PicUrl>
<Url><![CDATA[%s]]></Url>
</item>
"""

def make_item(book, itemindex):
    title = u'%s\t%s分\n%s\n%s\t%s' % (book['title'], book['rating']['average'], 
        ','.join(book['author']), book['publisher'], book['price'])
    description = ''
    picUrl = book['images']['large'] if itemindex == 1 else book['images']['small']
    url = re.sub('http://douban','http://m.douban', book['alt'])
    item = NEWS_MSG_ITEM_TPL % (title, description, picUrl, url)
    return item

#图文格式消息只有单独一条时，可以显示更多的description信息，所以单独处理
def make_single_item(book):
    title = u'%s\t%s分' % (book['title'], book['rating']['average'])
    description = '%s\n%s\t%s' % (','.join(book['author']), book['publisher'], book['price'])
    picUrl = book['images']['large']
    url = re.sub('http://douban','http://m.douban', book['alt'])
    item = NEWS_MSG_ITEM_TPL % (title, description, picUrl, url)
    return item


if __name__ == '__main__':
    app.run()
