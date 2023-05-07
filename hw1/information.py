from utils import *
from element import *


def get_information(name, element, num):
    url = "https://ptable.com/JSON/properties-90d5338.json"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
    Chrome/55.0.2883.87 Safari/537.36'}
    r = requests.get(url, headers=headers)
    hjson = json.loads(r.text)
    # 稀有气体没有熔点
    try:
        element.melting_point = hjson[num]['melt']
    except:
        element.melting_point = 'N/A'
    element.boiling_point = hjson[num]['boil']
    element.crust = hjson[num]["abundance"]['crust']
    try:
        element.meteor = hjson[num]["abundance"]['meteor']
    except:
        element.meteor = 'N/A'
    element.ocean = hjson[num]["abundance"]['ocean']
    element.solar = hjson[num]["abundance"]['solar']
    element.universe = hjson[num]["abundance"]['universe']
    element.discover = hjson[num]["discover"]