from element import *
from bs4 import BeautifulSoup
import requests


def get_melt_point(name, element):
    url = "https://ptable.com/?lang=zh-hans#%E6%80%A7%E8%B4%A8/%E7%86%94%E7%82%B9"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
    Chrome/55.0.2883.87 Safari/537.36'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    soup.prettify()
    element_table = soup.find_all(id='Ptable')  # elements' name can be only find in this part
    element_infor = element_table[0].find_all("abbr", string=name)
    element_infor = element_infor[0].parent
    element.melting_point = element_infor[0].data.string
