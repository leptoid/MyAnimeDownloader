#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import requests
import base64
import urllib3
from bs4 import BeautifulSoup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from downloader import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# TODO: Make it track missed episodes and retry when done


class WCOStream(object):

    def __init__(self, args):
        # Define our variables
        self.dl = Downloader()
        self.url = args['input'][0]
        self.resolution = args['resolution']
        self.logger = args['logger']
        self.season = args['season']
        self.ep_range = args['range']
        self.exclude = args['exclude']
        self.newest = args['newest']
        self.output = args['output']
        self.settings = args['settings']
        self.output_saver = args['outputsaver']
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        self.header = {
            'User-Agent': self.user_agent, 'Accept': '*/*', 'Referer': self.url, 'X-Requested-With': 'XMLHttpRequest'
        }
        self.base_url = "https://wcostream.com"
        self.path = os.path.dirname(os.path.realpath(__file__))

        # Check if the URL is valid
        valid_link, extra = self.is_valid()
        if valid_link:
            # Check to see if we are downloading a single episode or multiple
            if extra[0] == "anime/":
                # We are downloading multiple episodes
                print("Downloading show")
                self.download_show()
            else:
                # We are downloading a single episode
                print('Downloading single')
                self.download_single(extra)
        else:
            # Not a valid wcostream link
            print(extra)
            exit()

    def check_output(self, anime_name):
        if self.output is None:
            if self.settings.get_setting('useKnownDownloadLocation'):
                if anime_name in self.output_saver.savedLocation:
                    self.output = self.output_saver.get_location(anime_name)
            if self.settings.get_setting('defaultOutputLocation'):
                self.output = self.settings.get_setting('defaultOutputLocation')
            if self.output is None:
                self.output = os.path.abspath("Output" + os.sep + str(anime_name) + os.sep)
                if not os.path.exists("Output"):
                    os.makedirs("Output")
                if not os.path.exists(self.output):
                    os.makedirs(self.output)
        else:
            if self.output[-1] in ('/', '\\') and len(self.output) > 1:
                self.output = self.output[:-1]
            if self.output == ".":
                self.output = os.getcwd()
            if self.settings.get_setting('saveDownloadLocation'):
                self.output.translate(str.maketrans({'\\': os.sep, '/': os.sep}))
                self.output_saver.set_location(anime_name, self.output)
        if not os.path.exists(self.output):
            print('The specified path does not exist please create it: {0}'.format(self.output))
            exit(1)
        return self.output

    def request_c(self, url, extraHeaders=None):
        myheaders = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }
        if extraHeaders:
            myheaders.update(extraHeaders)

        cookie = None
        response = requests.get(url, headers=myheaders, verify=False, cookies=cookie, timeout=10)

        return response

    def find_download_link(self, url):
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        script_url = soup.find("meta", {"itemprop": "embedURL"}).next_element.next_element.text
        letters = script_url[script_url.find("[") + 1:script_url.find("]")]
        ending_number = int(re.search(' - ([0-9]+)', script_url).group(1))
        hidden_url = self._decode(letters.split(', '), ending_number)
        return self.get_download_url(hidden_url)[0]

    def _decode(self, array, ending):
        iframe = ''
        for item in array:
            decoded = base64.b64decode(item).decode('utf8')
            numbers = re.sub('[^0-9]+', '', decoded)
            # print(chr(int(numbers) - ending))
            iframe += chr(int(numbers) - ending)
        html = BeautifulSoup(iframe, 'html.parser')
        return self.base_url + html.find("iframe")['src']

    def download_single(self, extra):
        download_url = self.find_download_link(self.url)
        if self.resolution == '480':
            download_url = download_url[0][1]
        else:
            download_url = download_url[1][1]
        show_info = self.info_extractor(extra)
        output = self.check_output(show_info[0])
        args = []
        args.append(download_url)
        args.append(output)
        args.append(self.header)
        args.append(show_info)
        args.append(self.settings)
        self.dl.wco_dl(args)

    def download_show(self):
        page = requests.get(self.url)
        soup = BeautifulSoup(page.content, 'html.parser')
        ep_range = self.ep_range
        links = []
        for link in soup.findAll('a', {'class': 'sonra'}):
            if link['href'] not in links:
                links.append(link['href'])

        if self.exclude is not None:
            if "," not in self.exclude[0]:
                self.exclude[0] = "{0},{0}".format(self.exclude[0])
            excluded = [i for e in self.exclude[0].split(",") for i in links if re.search(e, i)]
            links = [item for item in links if item not in excluded]
        season = "season-" + self.season
        
        if "-" not in ep_range and ep_range != 'All':
            ep_range = '{0}-{0}'.format(ep_range)

        if ep_range == 'l5' or ep_range == 'L5':  # L5 (Last five)
            links = links[:5]
            ep_range = 'All'
            season = 'season-All'

        if self.newest:  # True or False
            links = links[0:1]
            ep_range = 'All'
            season = 'season-All'

        if season != "season-All" and ep_range != "All":
            episodes = ["episode-{0}".format(n) for n in
                        range(int(ep_range.split('-')[0]), int(ep_range.split('-')[1]) + 1)]
            if season == 'season-1':
                matching = [s for s in links if 'season' not in s or season in s]
            else:
                matching = [s for s in links if season in s]
            matching = [s for s in matching for i in episodes if i == re.search(r'episode-[0-9]+', s).group(0)]
        elif season != "season-All":
            if season == 'season-1':
                matching = [s for s in links if 'season' not in s or season in s]
            else:
                matching = [s for s in links if season in s]
        elif ep_range != 'All':
            episodes = ["episode-{0}".format(n) for n in
                        range(int(ep_range.split('-')[0]), int(ep_range.split('-')[1]) + 1)]
            matching = [s for s in links for i in episodes if re.search("{0}-".format(i), s)]
        else:
            matching = links

        if len(matching) > 1:
            matching.reverse()
        for item in matching:
            download_url = self.find_download_link(item)
            if self.resolution == '480':
                download_url = download_url[0][1]
            else:
                download_url = download_url[1][1]
            show_info = self.info_extractor(item)
            output = self.check_output(show_info[0])
            args = []
            args.append(download_url)
            args.append(output)
            args.append(self.header)
            args.append(show_info)
            args.append(self.settings)
            self.dl.wco_dl(args)

    def info_extractor(self, url):
        url = re.sub('https://www.wcostream.com/', '', url)
        try:
            if "season" in url:
                show_name, season, episode, desc = re.findall(r'([a-zA-Z0-9].+)\s(season\s\d+\s?)(episode\s\d+\s)?(.+)',
                                                              url.replace('-', ' '))[0]
            else:
                show_name, episode, desc = re.findall(r'([a-zA-Z0-9].+)\s(episode\s\d+\s?)(.+)', url.replace(
                    '-', ' '))[0]
                season = "season 1"
        except:
            show_name = url
            season = "Season 1"
            episode = "Episode 0"
            desc = ""
        if self.settings.get_setting('saveShowURL') and self.output_saver.get_show_url(show_name.title().strip()) == None:
            self.output_saver.set_show_url(show_name.title().strip(), url)
        return show_name.title().strip(), season.title().strip(), episode.title().strip(), desc.title().strip(), url

    def is_valid(self):
        website = re.findall('https://(www.)?wcostream.com/(anime/)?([a-zA-Z].+$)?', self.url)
        if website:
            if website[0][1] == "anime/":
                return True, (website[0][1], website[0][2])
            return True, website[0][2]
        return False, '[wco-dl] Not correct wcostream website.'

    def get_download_url(self, embed_url):
        page = self.request_c(embed_url)
        html = page.text

        # Find the stream URLs.
        if 'getvid?evid' in html:
            # Query-style stream getting.
            source_url = re.search(r'get\("(.*?)"', html, re.DOTALL).group(1)

            page2 = self.request_c(
                self.base_url + source_url,
                extraHeaders={
                    'User-Agent': self.user_agent, 'Accept': '*/*', 'Referer': embed_url,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            )
            if not page2.ok:
                raise Exception('Sources XMLHttpRequest request failed')
            json_data = page2.json()

            # Only two qualities are ever available: 480p ("SD") and 720p ("HD").
            source_urls = []
            sd_token = json_data.get('enc', '')
            hd_token = json_data.get('hd', '')
            source_base_url = json_data.get('server', '') + '/getvid?evid='
            if sd_token:
                source_urls.append(('480 (SD)', source_base_url + sd_token))  # Order the items as (LABEL, URL).
            if hd_token:
                source_urls.append(('720 (HD)', source_base_url + hd_token))
            # Use the same backup stream method as the source: cdn domain + SD stream.
            backup_url = json_data.get('cdn', '') + '/getvid?evid=' + (sd_token or hd_token)
        else:
            # Alternative video player page, with plain stream links in the JWPlayer javascript.
            sources_block = re.search(r'sources:\s*?\[(.*?)\]', html, re.DOTALL).group(1)
            stream_pattern = re.compile(r'\{\s*?file:\s*?"(.*?)"(?:,\s*?label:\s*?"(.*?)")?')
            source_urls = [
                # Order the items as (LABEL (or empty string), URL).
                (sourceMatch.group(2), sourceMatch.group(1))
                for sourceMatch in stream_pattern.finditer(sources_block)
            ]
            # Use the backup link in the 'onError' handler of the 'jw' player.
            backup_match = stream_pattern.search(html[html.find(b'jw.onError'):])
            backup_url = backup_match.group(1) if backup_match else ''
        # print("debug:", backupURL)
        # print("debug:", sourceURLs)

        return source_urls, backup_url
