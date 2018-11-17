import requests
import re 
import json 
from requests.exceptions import RequestException
import time
from bs4 import BeautifulSoup

def get_one_page(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36'
        }
        response = requests.get(url, headers = headers)
        if response.status_code == 200:
            return response.text 
        return None 
    except RequestException:
        return None 

def parse_one_page(html):
    soup = BeautifulSoup(html, 'lxml')
    for item in soup.find_all(name='dd'):
        yield {
            'index': item.i.text,
            'image': item.a.find_all(attrs = {'class': 'board-img'})[0].attrs['data-src'],
            'title': item.a.attrs['title'],
            'actor': item.find(attrs={'class': 'star'}).text.strip()[3:],
            'time': item.find(attrs={'class': 'releasetime'}).text.strip()[5:],
            'score': item.find(attrs={'class': 'integer'}).text + item.find(attrs={'class': 'fraction'}).text
        }

    # pattern = re.compile('<dd>.*?board-index.*?>(\d+)</i>.*?data-src="(.*?)".*?name"><a'
    #                      + '.*?>(.*?)</a>.*?star">(.*?)</p>.*?releasetime">(.*?)</p>'
    #                      + '.*?integer">(.*?)</i>.*?fraction">(.*?)</i>.*?</dd>', re.S)
    # items = re.findall(pattern, html)
    # for item in items:
    #     yield {
    #         'index': item[0],
    #         'image': item[1],
    #         'title': item[2],
    #         'actor': item[3].strip()[3:],
    #         'time': item[4].strip()[5:],
    #         'score': item[5] + item[6]
    #     }

def write_to_file(content):
    with open('result.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps(content, ensure_ascii=False) + '\n')

def main(offset):
    url = 'http://maoyan.com/board/4?offset+'+str(offset)
    html = get_one_page(url)

    for item in parse_one_page(html):
        write_to_file(item)

if __name__ == '__main__':
    for i in range(10):
        main(i*10)
        time.sleep(1)
