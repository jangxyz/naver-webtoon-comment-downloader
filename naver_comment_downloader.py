#!/usr/bin/python
# -*- coding: utf8 -*-

import sys, os

usage = '''

    retrieve comments from naver webtoon

    다운로드(만화ID, 만화번호 or 날짜):
        $ python naver_comment_downloader.py 20853 tue
        $ python naver_comment_downloader.py 20853 2011.06.21
        $ python naver_comment_downloader.py 20853 535
        $ python naver_comment_downloader.py http://comic.naver.com/webtoon/detail.nhn?titleId=20853&no=535&weekday=fri

    특정 만화 나열(만화ID):
        $ python naver_comment_downloader.py 20853 

    제목으로 만화 검색:
        $ python naver_comment_downloader.py '마음의 소리' 

    전체 만화 나열:
        $ python naver_comment_downloader.py 

'''
import datetime, time
import urllib, urllib2
import BeautifulSoup
import json
import htmlentitydefs
import re
import random

from collections import defaultdict

COMMENT_URL                = 'http://comic.naver.com/comments/list_comment.nhn' 
DAILY_WEBTOON_URL_TEMPLATE = 'http://comic.naver.com/webtoon/weekdayList.nhn?week=%(day)s'
WEBTOON_LIST_URL_TEMPLATE  = 'http://comic.naver.com/webtoon/list.nhn?titleId=%(title_id)d'
WEEKDAY_URL                = 'http://comic.naver.com/webtoon/weekday.nhn'
#DETAIL_URL_TEMPLATE        = 'http://comic.naver.com/webtoon/detail.nhn?titleId=%(title_id)d&no=%(no)d&weekday=%(weekday)s'
DETAIL_URL_TEMPLATE        = 'http://comic.naver.com/webtoon/detail.nhn?titleId=%(title_id)d&no=%(no)d'

WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

#--data 'ticket=comic1&object_id=63453_112&_ts=1308977593289&lkey=qQ85K2dXciaSotohX3m3OXzKREPC6mnVXvGI8imO3XadMfSyoyRxtQ&page_size=15&page_no=3' --referer 'http://comic.naver.com/webtoon/detail.nhn?titleId=63453&no=112&weekday=sat'

def soup_open(url):
    html = urllib.urlopen(url).read()
    soup = BeautifulSoup.BeautifulSoup(html)
    return soup

def fetch_lkey(title_id, no):
    url = DETAIL_URL_TEMPLATE  % locals()
    soup = soup_open(url)

    scripts = soup.findAll('script', type='text/javascript')
    scripts = [s for s in scripts if 'lkey' in str(s)]

    lkey = [line for line in str(scripts[0]).split("\n") if 'lkey' in line]
    lkey = lkey[0].strip().split(':')[-1].strip(" '")
    return lkey

def fetch_comment_for_page(title_id, no, page_no, lkey=None):
    ticket    = 'comic1'
    object_id = "%d_%d" % (title_id, no)
    page_size = 15
    referer   = DETAIL_URL_TEMPLATE % locals()
    _ts       = int(time.time() * 1000)
    if not lkey:
        lkey  = fetch_lkey(title_id, no)

    data = [(k,v) for k,v in locals().items() if k in ['ticket', 'object_id', '_ts', 'lkey', 'page_size', 'page_no']]
    #
    opener = urllib2.build_opener()
    opener.addheaders.append(('referer', referer))
    resp = opener.open(COMMENT_URL, data=urllib.urlencode(data), timeout=10)
    text = resp.read()
    text = text.decode('utf8')
    text = text.replace("\\'", "'")
    #text = text.replace('\\"', '"')
    #text = text.replace("\\", r"\\")
    #text = text.replace(r'\\"', '\\"')
    # '\\\\"'   --> '\\\\"'
    # '\\>'     --> '\\\\>'
    # r'\\지금' --> r'\\\\지금'
    text = re.sub(r'(\\+)([^"\\])', lambda match: "%s%s%s" % (match.group(1),match.group(1),match.group(2)), text)

    # exception: on (183559, 49, 101)
    text = text.replace(
        '"visible_yn":"Y",,"is_mine":"N",',
        '"visible_yn":"Y","is_mine":"N",'
    )

    return text

def fetching_comments(title_id, no):
    #ticket    = 'comic1'
    #object_id = "%d_%d" % (title_id, no)
    lkey      = fetch_lkey(title_id, no)
    #page_size = 15
    #referer   = DETAIL_URL_TEMPLATE % locals()
    #_ts       = int(time.time() * 1000)
    #page_no   = 1

    #data = [(k,v) for k,v in locals().items() if k in ['ticket', 'object_id', '_ts', 'lkey', 'page_size', 'page_no']]
    ##
    #opener = urllib2.build_opener()
    #opener.addheaders.append(('referer', referer))
    #resp = opener.open(COMMENT_URL, data=urllib.urlencode(data), timeout=10)
    #text = resp.read()
    page_no = 1
    page_size = 15
    text = fetch_comment_for_page(title_id, no, page_no, lkey)
    j = json.loads(text)

    print j['total_count'], 'comments'
    comment_list = j['comment_list']
    for comment in comment_list:
        yield comment, j

    while j['total_count'] > page_no * page_size:
        error_count = 0

        for error_count in range(3):
            try:
                page_no = j['page_no'] + 1
                #_ts  = int(time.time() * 1000)
                ##
                #data = [(k,v) for k,v in locals().items() if k in ['ticket', 'object_id', '_ts', 'lkey', 'page_size', 'page_no']]
                #text = opener.open(COMMENT_URL, data=urllib.urlencode(data)).read()
                text = fetch_comment_for_page(title_id, no, page_no, lkey)
                #text = text.replace("\\'", "'")
                j = json.loads(text)
                #
                for comment in j['comment_list']:
                    yield comment, j

                break
            except Exception, e:
                error_count += 1
                random_sleep = random.randrange(10)+1

                p("[ERROR #%d] %s" % (error_count, e))
                p(text.strip())
                p("sleeping for %d seconds.." % random_sleep)
                time.sleep(random_sleep)

                lkey = fetch_lkey(title_id, no)
                j['page_no'] = page_no - 1
                continue
        else:
            p('too many errors!')
            sys.exit(1)

        #
        time.sleep(1)


def fetch_comments(title_id, no):
    comments = []
    prev_j = None
    for comment, j in fetching_comments(title_id, no):
        comments.append(comment['contents'])

        if j != prev_j:
            first_comment = j['comment_list'][0]
            print " * page %d (%.1f %%): [%s] %s" % (
                j['page_no'], 
                len(comments) *100.0 / j['total_count'],
                first_comment["registered_ymdt"], unescape(first_comment["contents"]).replace("\r\n", "")[:40])

        prev_j = j

    return comments


def fetch_all_webtoons():
    ''' return title_id, name and day '''
    webtoon_list = []
    # retrieve
    soup = soup_open(WEEKDAY_URL)
    # parse
    daily_all = soup.find('div', {'class': 'list_area daily_all'})
    for daily_ul in daily_all.findAll('ul'):
        for li in daily_ul.findAll('li'):
            a = li.find('a', {'class':'title'})
            name     = a['title']
            title_id = get_title_id_from_href(a['href'])
            weekday  = get_weekday_from_href(a['href'])
            #
            webtoon_list.append((title_id, name, weekday))
    return webtoon_list


def fetch_webtoons_list(day):
    ''' return names and title_ids of webtoons on a given day 
    
    from daily webtoon page : http://comic.naver.com/webtoon/weekdayList.nhn?week=sat
    '''
    url = DAILY_WEBTOON_URL_TEMPLATE % {'day': convert_day(day)}
    soup = soup_open(url)

    webtoons = []
    img_list = soup.find('ul', {'class': 'img_list'})
    for li in img_list.findAll('li'):
        a = li.dl.dt.a
        title = a.text
        title_id = get_title_id_from_href(a['href'])
        webtoons.append((title, title_id))
    return webtoons

def fetch_webtoon_info_list(title_id):
    ''' return (no, subject, url, date) of specific webtoon. '''
    url = WEBTOON_LIST_URL_TEMPLATE % locals()
    soup = soup_open(url)
    # parse
    title = soup.find('div', {'class':'detail'}).h2.text

    webtoon_list = []
    view_list = soup.find('table', {'class':"viewList"})
    valid_trs = [tr for tr in view_list.findAll('tr') if len(tr.findAll('td')) >= 4]
    for tr in valid_trs:
        a = tr.find('td', {'class':'title'}).a
        subject = a.text.strip()
        href = a['href']
        no = get_no_from_href(href)
        date = tr.find('td', {'class':'num'}).text
        date = datetime.datetime.strptime(date, "%a %b %d %X %Z %Y")
        #
        webtoon_list.append( (no, subject, get_domain(url, href), date) )
    return (title, webtoon_list)


# ----
# util
# ----

def get_webtoon_title_from_title_id(title_id):
    return fetch_webtoon_info_list(title_id)[0]

def get_no_from_date(title_id, date):
    date_str = date.strftime("%Y.%m.%d")
    for no, subject, url, _date in fetch_webtoon_info_list(title_id)[1]:
        if date_str == _date.strftime("%Y.%m.%d"):
            return no

def convert_day(day):
    ''' convert day into abbreviated day of week '''
    if isinstance(day, datetime.datetime) or isinstance(day, datetime.date):
        return day.strftime("%a").lower()
    if isinstance(day, basestring):
        if ' ' not in day.strip():
            if day.endswith('day'):
                day = day.partition("day")[0]
            if day.endswith("요일"):
                day = day.partition("요일")[0]

        if day.lower() in WEEKDAYS:
            return day.lower()
        elif day in ['월', '화', '수', '목', '금', '토', '일']:
            return {
                '월': 'mon',
                '화': 'tue',
                '수': 'wed',
                '목': 'thu',
                '금': 'fri',
                '토': 'sat',
                '일': 'sun'
            }[day]

    raise Exception("cannot convert: " + day)


def get_domain(url, path=None):
    '''
        urlparse:
            <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
    '''
    parse_result = urllib2.urlparse.urlparse(url)
    domain = '''%(scheme)s://%(netloc)s''' % parse_result._asdict()
    domain = domain.rstrip('/')
    # paste path if any
    if path:
        return domain + "/" + unescape(path).lstrip('/')
    return domain

def unescape(text, repeat=None):
    ''' from http://effbot.org/zone/re-sub.htm#unescape-html '''
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    new_text = re.sub("&#?\w+;", fixup, text)
    # once
    if repeat is None:
        return new_text
    # repeat for specified times, until no change
    repeat_count = 0
    while new_text != text:
        text = new_text
        new_text = re.sub("&#?\w+;", fixup, text)
        #
        repeat_count += 1
        if repeat is True: 
            continue
        elif repeat_count >= repeat:
            break
    #
    return new_text

def get_title_id_from_href(href):
    query = href.rsplit('?', 1)[-1]
    title_id = dict(map(urllib.splitvalue, query.split('&')))['titleId']
    return int(title_id)

def get_weekday_from_href(href):
    query = href.rsplit('?', 1)[-1]
    weekday = dict(map(urllib.splitvalue, query.split('&')))['weekday']
    return weekday

def get_no_from_href(href):
    query = href.rsplit('?', 1)[-1]
    no = dict(map(urllib.splitvalue, query.split('&')))['no']
    return int(no)

def compute_date_from_weekday(weekday):
    #
    today = datetime.datetime.today()
    today_weekday = today.strftime("%a").lower()
    # earlier than today
    date_offset = WEEKDAYS.index(weekday) - WEEKDAYS.index(today_weekday)
    if date_offset > 0:
        date_offset -= 7
    day = today + datetime.timedelta(days=date_offset)
    return day


def p(*s):
    for x in s:
        if isinstance(x, basestring):
            x = x.encode(sys.getfilesystemencoding())
        print(x),
    print

# -----------
# application
# -----------

def print_all_webtoons():
    # fetch
    webtoons = fetch_all_webtoons()

    webtoons_by_weekday = defaultdict(list)
    for (title_id, name, weekday) in webtoons:
        webtoons_by_weekday[weekday.lower()].append((title_id, name))

    for weekday in WEEKDAYS:
        print "=", weekday.title(), "="
        for title_id, name in sorted(webtoons_by_weekday[weekday], key=lambda x: x[0]):
            print " * [%6d] %s" % (title_id, name)
        print

def print_day_webtoon(weekday):
    # fetch
    webtoons = fetch_all_webtoons()

    webtoons_by_weekday = defaultdict(list)
    for (title_id, name, _weekday) in webtoons:
        webtoons_by_weekday[_weekday.lower()].append((title_id, name))

    print "=", weekday.title(), "="
    for title_id, name in sorted(webtoons_by_weekday[weekday], key=lambda x: x[0]):
        print " * [%6d] %s" % (title_id, name)
    print

def search_webtoon(webtoon_title):
    # find webtoon
    matches = []
    webtoon_title = webtoon_title.decode(sys.getfilesystemencoding())
    webtoons = fetch_all_webtoons()

    # 1. exact match ignoring space 
    webtoon_title_wo_space = webtoon_title.replace(' ', '')
    for (title_id, name, day) in webtoons:
        if webtoon_title_wo_space == name.replace(u' ', u''):
            matches.append( (title_id, name, day) )

    # 2. partial match ignoring space
    if not matches:
        for (title_id, name, day) in webtoons:
            if webtoon_title_wo_space in name.replace(u' ', u''):
                matches.append( (title_id, name, day) )

    #
    if len(matches) == 0:
        print "'%s'와 맞는 웹툰을 찾을 수 없습니다." % webtoon_title
    elif len(matches) == 1:
        webtoon = matches[0]
        p(u"<%s> [%d] %s" % (webtoon[2].title(), webtoon[0], webtoon[1]))
    else:
        p(u'웹툰 %d개를 찾았습니다.' % len(matches))
        for webtoon in matches:
            p(u" * <%s> [%6d] %s" % (webtoon[2].title(), webtoon[0], webtoon[1]))

def print_webtoon_info(title_id):
    title, webtoon_info = fetch_webtoon_info_list(title_id)
    p(u"= %s =" % title)
    for no,subject,url,date in webtoon_info:
        p(u' * [%s] #%d: "%s"' % (date.strftime("%Y.%m.%d (%a)"), no, subject))

def download_webtoon_comments_from_url(url):
    title_id = get_title_id_from_href(url)
    no = get_no_from_href(url)
    return download_webtoon_comments(title_id, no)

def download_webtoon_comments(title_id, arg):
    '''
        $ python naver_comment_downloader.py 20853 tue
        $ python naver_comment_downloader.py 20853 2011.06.21
        $ python naver_comment_downloader.py 20853 535
    '''
    title_id = int(title_id)
    title = get_webtoon_title_from_title_id(title_id)
    
    if arg.lower() in WEEKDAYS:
        date = compute_date_from_weekday(arg.lower())
        no = get_no_from_date(title_id, date)
    elif re.match("^[0-9]{4}[.][0-9]{2}[.][0-9]{2}$", arg):
        date = datetime.datetime.strptime(arg, "%Y.%m.%d")
        no = get_no_from_date(title_id, date)
    elif arg.isdigit():
        no = int(arg)

    # save
    output_filename = "%s_%d.txt" % (title, no)
    out = open(output_filename, 'w')

    # fetch comments
    prev_j = None
    for i,(comment, j) in enumerate(fetching_comments(title_id, no)):

        #for comment, j in fetching_comments(title_id, no):
        #comments.append(comment['contents'])

        if j != prev_j:
            first_comment = j['comment_list'][0]
            p(u" * page %d (%.1f %%): [%s] %s" % (
                j['page_no'], 
                (i+1) *100.0 / j['total_count'],
                first_comment["registered_ymdt"], unescape(first_comment["contents"]).replace("\r\n", "")[:40]))

        content = unescape(comment['contents']).replace("\n", "")
        out.write(content.encode(sys.getfilesystemencoding()))
        out.write("\n")

        prev_j = j

    out.close()
    p(i+1, u'comments successfully saved at', output_filename)


def main(args):
    if len(args) == 1:
        print_all_webtoons()
    elif len(args) == 2:
        # help
        if args[1].lower() in ('--help', '-h'):
            print usage.strip()
            return

        sys.stderr.write('type --help to see help\n')
        if args[1].startswith("http://"):
            download_webtoon_comments_from_url(args[1])
        elif args[1].isdigit():
            print_webtoon_info(int(args[1]))
        elif args[1].lower() in WEEKDAYS:
            print_day_webtoon(args[1].lower())
        else:
            search_webtoon(args[1])

    elif len(args) == 3:
        download_webtoon_comments(*args[1:])

if __name__ == '__main__':
    main(sys.argv)

