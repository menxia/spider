from requests import Session 
from weixin.config import * 
from weixin.db import RedisQueue
from weixin.mysql import MySQL
from weixin.request import WeixinRequest 
from urllib.parse import urlencode 
import requests 
from pyquery import  PyQuery as pq 
from requests import ReadTimeout, ConnectionError

class Spider():
    base_url = 'http://weixin.sogou.com/weixin'
    keyword = 'NBA'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,ja;q=0.4,zh-TW;q=0.2,mt;q=0.2',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': 'SUV=00670A2227B2ABC254DA3D7FD4C0C627; ssuid=8733545508; SUID=07C4CF8C771C900A54BC59A80005FA70; CXID=A448FA79C6A209243C989A4E8B73B7D8; ad=CWjGyZllll2bUpBolllllVsBwh9lllllhX0$pZllll9lllll4h7ll5@@@@@@@@@@; sw_uuid=2614289524; sg_uuid=828389127; pex=C864C03270DED3DD8A06887A372DA219231FFAC25A9D64AE09E82AED12E416AC; IPLOC=CN3100; ABTEST=1|1542847064|v1; SNUID=5EB02193595C226F4A6FCFB45A39C0AD; weixinIndexVisited=1; JSESSIONID=aaaH6l1zlTIDSfIvo71Bw; ppinf=5|1543052130|1544261730|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZTo2OmZhbmZhbnxjcnQ6MTA6MTU0MzA1MjEzMHxyZWZuaWNrOjY6ZmFuZmFufHVzZXJpZDo0NDpvOXQybHVFbWMtN0pFVEVBcG9fVExPZFRWZ25JQHdlaXhpbi5zb2h1LmNvbXw; pprdig=KsCn3kz7vFkBhBco6qspL2OfbKIVQayZoSqYAcBkWHZ2q28BR-A6z5u_JvcFoZCcdUsBpYHyVjPKLmk78v97jTSiiC4eT8Kgwy5F8p1Cv-KjkzWwYJ2iCIPX1jTrizrKOE5k6me2ap-WYBYIGSx5Xb0pkU7TlfgtWCrvk3mSNak; sgid=12-38089007-AVv5G2Kr8FBOCPPiccG54jibQ; ppmdig=1543052130000000812df3126ffd3a9ba45c73998d7660ec',
        'Host': 'weixin.sogou.com',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
    }
    session = Session() 
    queue = RedisQueue()
    mysql = MySQL()

    def __init__(self):
        self.id = 1

    def get_proxy(self):
        try:
            response = requests.get(PROXY_POOL_URL)
            if response.status_code == 200:
                print('Get Proxy', response.text)
                return response.text
            return None
        except requests.ConnectionError:
            return None
    
    def start(self):
        self.session.headers.update(self.headers)
        start_url = self.base_url+ '?' + urlencode({'query': self.keyword, 'type': 2})
        weixin_request = WeixinRequest(url=start_url, callback=self.parse_index, need_proxy=True)
        self.queue.add(weixin_request)

    def schedule(self):
        while not self.queue.empty():
            weixin_request = self.queue.pop()
            callback = weixin_request.callback
            print('Schedule', weixin_request.url)
            response = self.request(weixin_request)
            print(response)
            if response and response.status_code in VALID_STATUSES+[301]:
                results = list(callback(response))
                if results:
                    for result in results:
                        print('New Result', type(result))
                        if isinstance(result, WeixinRequest):
                            self.queue.add(result)
                        if isinstance(result, dict):
                            print(result)
                            self.mysql.insert('articles', result)
                            # print('##########insert into database################')
                else:
                    self.error(weixin_request)
            else:
                self.error(weixin_request)
    
    def request(self, weixin_request):
        try:
            if weixin_request.need_proxy:
                proxy = self.get_proxy()
                if proxy:
                    proxies = {
                        'http': 'http://' + proxy,
                        'https': 'https://' + proxy
                    }
                    return self.session.send(weixin_request.prepare(),
                                             timeout=weixin_request.timeout, allow_redirects=False, proxies=proxies)
            return self.session.send(weixin_request.prepare(), timeout=weixin_request.timeout, allow_redirects=True)
        except (ConnectionError, ReadTimeout) as e:
            print(e.args)
            return False
    
    def error(self, weixin_request):
        weixin_request.fail_time = weixin_request.fail_time + 1
        print('Request Failed', weixin_request.fail_time, 'Times', weixin_request.url)
        if weixin_request.fail_time < MAX_FAILED_TIME:
            self.queue.add(weixin_request)
    
    def parse_index(self, response):
        """
        解析索引页
        :param response: 响应
        :return: 新的响应
        """
        doc = pq(response.text)
        items = doc('.news-box .news-list li .txt-box h3 a').items()
        for item in items:
            url = item.attr('href')
            weixin_request = WeixinRequest(url=url, callback=self.parse_detail)
            yield weixin_request
        next = doc('#sogou_next').attr('href')
        if next:
            url = self.base_url + str(next)
            weixin_request = WeixinRequest(url=url, callback=self.parse_index, need_proxy=True)
            yield weixin_request

    def parse_detail(self, response):
        doc = pq(response.text)
        data = {
            # 'id': self.id,
            'title': doc('.rich_media_title').text(),
            'content': doc('.rich_media_content').text(),
            'date': doc('#post-date').text(),
            'nickname': doc('#js_profile_qrcode > div > strong').text(),
            'wechat': doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
        }
        yield data

    def run(self):
        self.start() 
        self.schedule()