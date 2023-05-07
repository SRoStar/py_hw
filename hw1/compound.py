from utils import *


def find_compound(name):
    url = "https://ptable.com/JSON/compounds/formula=" + name
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
        Chrome/55.0.2883.87 Safari/537.36'}
    r = requests.get(url, headers=headers)
    hjson = json.loads(r.text)
    result = []
    count = 0
    for com_dic in hjson['matches']:
        com_name = com_dic['molecularformula']
        if name in com_name and len(com_name) != len(name):
            if len(name) == 2:
                result.append(com_name)
                count = count + 1
            else:
                pos = com_name.find(name)
                if pos == len(name) + 1 and pos != 1 and '^' not in com_name:
                    result.append(com_name)
                    count = count + 1
        if count >= 3:
            break
    return result




def main():
    name = 'H'
    temp = find_compound(name)
    print(temp)


if __name__ == '__main__':
    main()
