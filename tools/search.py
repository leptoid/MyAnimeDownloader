
import re
import requests
from bs4 import BeautifulSoup


class Search:
    def __init__(self):
        self.base_url = "https://www.wcostream.com"
        pass

    def start(self):
        get_url = input('Is this [(S)ubbed/(D)ubbed/(C)artoon]: ')
        find_me = input('Input the show you are looking for: ')
        find_me = find_me.replace(' ', '-').lower()

        if get_url.lower() in ['', 's', 'sub', 'subbed']:
            url = "https://www.wcostream.com/subbed-anime-list"
        elif get_url.lower() in ['d', 'dub', 'dubbed']:
            url = "https://www.wcostream.com/dubbed-anime-list"
        else:
            url = "https://www.wcostream.com/cartoon-list"

        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        shows = soup.findAll('a')

        s_array = []

        for show in shows:
            try:
                if 'anime' in show['href']:
                    if find_me.startswith("^"):
                        if re.findall('^/anime/{0}'.format(find_me[1]), show['href']):
                            if show['href'] not in s_array:
                                s_array.append(show['href'])
                    else:
                        if re.findall(find_me, show['href']):
                            if show['href'] not in s_array:
                                s_array.append(show['href'])
            except:
                pass

        for item in s_array:
            print('{0}. {1} ({2})'.format(s_array.index(item) + 1,
                                          item.replace('/anime/', '').replace('-', ' ').title().strip(),
                                          self.base_url + item))
