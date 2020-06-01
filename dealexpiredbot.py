import praw
from datetime import datetime, timedelta, timezone
from configparser import ConfigParser
import requests
import time


class DealExpiredBot():

    def __init__(self):
        self.user_agent = "DealExpiredBot / V1.0 / By ScoopJr"
        print('Starting up...', self.user_agent)
        CONFIG = ConfigParser()
        CONFIG.read('config.ini')
        # Retrieving User information from config.ini for PRAW
        self.user = CONFIG.get('main', 'USER')
        self.password = CONFIG.get('main', 'PASSWORD')
        self.client = CONFIG.get('main', 'CLIENT_ID')
        self.secret = CONFIG.get('main', 'SECRET')
        self.subreddit = CONFIG.get('main', 'SUBREDDIT')
        self.token_url = "https://www.reddit.com/api/v1/access_token"
        self.token = ""
        self.t_type = ""
        self.delay = CONFIG.getint('main', 'DELAY')
        self.reddit = praw.Reddit(client_id=self.client,
                             client_secret=self.secret,
                             password=self.password,
                             user_agent=self.user_agent,
                             username=self.user)
        self.flair = CONFIG.get('main', 'FLAIR')
        self.days_before_flair = CONFIG.getint('main', 'DAYS_BEFORE_FLAIRING')
        self.td = timezone(-timedelta(hours=7), name="RPST")

        self.unixnow = datetime.timestamp(datetime.now(self.td.utc))

    def get_token(self):
        """Gets OAUTH access token for PRAW"""
        client_auth = requests.auth.HTTPBasicAuth(self.client, self.secret)
        post_data = {'grant_type': 'password', 'username': self.user, 'password': self.password}
        headers = {'User-Agent': self.user_agent}
        response = requests.Session()
        response2 = response.post(self.token_url, auth=client_auth, data=post_data, headers=headers)
        self.token = response2.json()['access_token']
        self.t_type = response2.json()['token_type']

    def convert_utc_to_local(self, utcstamp):
        """

        utcstamp: Takes a unix timestamp and converts it to America/Los Angeles time
        :return Returns a unix timestamp that accounts for tzinfo=America/Los Angeles
        """
        timez = timezone(-timedelta(hours=7), name="RTLA") #accounting for timezone in America/Los Angeles diff
        reddit_date = datetime.utcfromtimestamp(utcstamp) #turning created_utc integer into a datetime object
        timestamp = reddit_date.replace(tzinfo=timez).timestamp() #replacing tzinfo of None to the correct timezone
        return timestamp

    def get_days_between(self, utctoday, utcconverted):
        """

        :param utctoday: Takes in a datetime object that is aware, I.E. datetime.now() but accounting for Los Angeles time
        :param utcconverted: Times in a converted unix timestamp
        :return: The rounded amount of days between the two unix timestamps
        """
        return round(((utctoday - utcconverted)/(60*60*24)))



    def check_should_be_flaired(self, utc):
        """

        :param utc: Takes an created_utc from Reddit and converts it to aware unix datetime object
        :return: If the days passed is greater than the limit set by the user, return True, else return False I.E. Post made 3 days ago = 3 > 14 = False
        """
        days = self.get_days_between(self.unixnow, self.convert_utc_to_local(utc))
        if days > self.days_before_flair:
            return True
        else:
            return False



    def main(self):
        """Main - handling running of the bot"""

        while True:
            print(f"...Searching for posts that are older than: {self.days_before_flair} days")
            for post in self.reddit.subreddit(self.subreddit).stream.submissions(pause_after=1):
                if post is None:
                    break
                elif (post.link_flair_text == self.flair) or post.archived:
                    continue
                else:
                    post_check = self.check_should_be_flaired(post.created_utc)
                    if post_check:
                        post.mod.flair(self.flair)
                        print(f"Post: {post.id} flair changed to {self.flair}")
            print(f"...Taking a small break!  Be back in {self.delay} seconds")
            time.sleep(self.delay)







if __name__ == "__main__":
    bot = DealExpiredBot()
    bot.main()



