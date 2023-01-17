import requests
import json
import sys
import re
import os
from slugify import slugify

class Downloader(object):
    def __init__(
        self,
        cookie,
        download_path=os.environ.get('FILE_PATH', './data'),
        pk='BCpkADawqM2OOcM6njnM7hf9EaK6lIFlqiXB0iWjqGWUQjU7R8965xUvIQNqdQbnDTLz0IAO7E6Ir2rIbXJtFdzrGtitoee0n1XXRliD-RH9A-svuvNW9qgo3Bh34HEZjXjG4Nml4iyz3KqF',
        brightcove_account_id=3695997568001,
    ):
        self.cookie = cookie.strip().strip('"')
        self.download_path = download_path
        self.pk = pk.strip()
        self.brightcove_account_id = brightcove_account_id
        self.pythonversion = 3 if sys.version_info >= (3, 0) else 2

    def is_unicode_string(self, string):
        if (self.pythonversion == 3 and isinstance(string, str)) or (self.pythonversion == 2 and isinstance(string, unicode)):
            return True

        else:
            return False

    def download_course_by_url(self, url):
        m = re.match(r'https://www.skillshare.com/classes/.*?/(\d+)', url)

        if not m:
            raise Exception('Failed to parse class ID from URL')

        self.download_course_by_class_id(m.group(1))

    def download_course_by_class_id(self, class_id):
        data = self.fetch_course_data_by_class_id(class_id=class_id)
        teacher_name = None

        if 'vanity_username' in data['_embedded']['teacher']:
            teacher_name = data['_embedded']['teacher']['vanity_username']

        if not teacher_name:
            teacher_name = data['_embedded']['teacher']['full_name']

        if not teacher_name:
            raise Exception('Failed to read teacher name from data')

        if self.is_unicode_string(teacher_name):
            teacher_name = teacher_name.encode('ascii', 'replace')

        title = data['title']

        if self.is_unicode_string(title):
            title = title.encode('ascii', 'replace')  # ignore any weird char

        base_path = os.path.abspath(
            os.path.join(
                self.download_path,
                slugify(teacher_name),
                slugify(title),
            )
        ).rstrip('/')
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)

        for u in data['_embedded']['units']['_embedded']['units']:
            for s in u['_embedded']['sessions']['_embedded']['sessions']:
                video_id = None
                video_url = None
                if 'video_hashed_id' in s and s['video_hashed_id']:
                    video_id = s['video_hashed_id'].split(':')[1]
                    video_url = self.fetch_video_url_by_id(video_id)
                if not video_id:
                    raise Exception('Failed to read video ID from data')

                s_title = s['title']

                if self.is_unicode_string(s_title):
                    s_title = s_title.encode('ascii', 'replace')  # ignore any weird char

                file_name = '{} - {}'.format(
                    str(s['index'] + 1).zfill(2),
                    slugify(s_title),
                )

                file_path = os.path.join(base_path, file_name)
                with open(file_path, 'wb') as f:
                    response = requests.get(video_url, stream=True)
                    total_length = response.headers.get('content-length')
                    if total_length is None:  # no content length header
                        f.write(response.content)
                    else:
                        dl = 0
                        total_length = int(total_length)
                        for data in response.iter_content(4096):
                            dl += len(data)
                            f.write(data)
                            done = int(50 * dl / total_length)
                            sys.stdout.write("\r[%s%s] Downloading %s " % ('=' * done, ' ' * (50-done), file_name))    
                            sys.stdout.flush()
                print("\n")
    def fetch_course_data_by_class_id(self, class_id):
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9,fr;q=0.8',
            'content-type': 'application/json',
            'cookie': self.cookie,
            'origin': 'https://www.skillshare.com',
            'referer': 'https://www.skillshare.com/classes/{}'.format(class_id),
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
        }

        params = (
            ('class_id', class_id),
        )

        response = requests.get(
            'https://www.skillshare.com/classes/{}/playlist'.format(class_id), headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(
                'Failed to fetch course data, status code: {}, content: {}'.format(
                    response.status_code, response.text))

        return json.loads(response.text)

    def fetch_video_url_by_id(self, video_id):
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9,fr;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://www.skillshare.com',
            'referer': 'https://www.skillshare.com/',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
        }

        params = (
            ('video_id', video_id),
            ('account_id', self.brightcove_account_id),
            ('pk', self.pk),
        )

        response = requests.get(
            'https://edge.api.brightcove.com/playback/v1/accounts/{}/videos/{}'.format(
                self.brightcove_account_id, video_id), headers=headers, params=params)

        if response.status_code != 200:
                        raise Exception(
                'Failed to fetch video url, status code: {}, content: {}'.format(
                    response.status_code, response.text))

        video_data = json.loads(response.text)
        highest_resolution = None
        for source in video_data['sources']:
            if source['container'] == "MP4" and (highest_resolution is None or source['height'] > highest_resolution['height']):
                highest_resolution = source
        return highest_resolution['src']




