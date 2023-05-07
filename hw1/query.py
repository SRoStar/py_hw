from utils import *
from element import *
from information import *
from compound import *


def ele_query(name):
    url = "https://ptable.com/?lang=zh-hans#%E6%80%A7%E8%B4%A8/%E7%B3%BB%E5%88%97"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
    Chrome/55.0.2883.87 Safari/537.36'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    soup.prettify()
    element_table = soup.find_all(id='Ptable')  # elements' name can be only find in this part
    if 'a' <= name[0] <= 'z' or 'A' <= name[0] <= 'Z':
        element_infor = element_table[0].find_all("abbr", string=name)
    else:
        # the result of find_all is list,so it should be taken the first element
        element_infor = element_table[0].find_all("em", string=name)
        # for the sake of line feed, use previous_sibling two times
        name = element_infor[0].previous_sibling.previous_sibling.string
    element_infor = element_infor[0].parent
    # get element number
    ele_num = element_infor.b.string
    ele_wei = element_infor.data.string
    element = Element(name, ele_num, ele_wei)
    get_information(name, element, int(ele_num))
    element.compound = find_compound(name)
    return element


def main():
    name = 'Pb'
    element = ele_query(name)
    element.print()


if __name__ == '__main__':
    main()
