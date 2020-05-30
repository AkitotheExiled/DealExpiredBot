import praw
from praw.models.comment_forest import CommentForest
from configparser import ConfigParser
import requests
import time


class DealExpiredBot():

    def __init__(self):
        self.user_agent = "DealExpiredBot / V1.0 By ScoopJr"
        print('Starting up...', self.user_agent)
        CONFIG = ConfigParser()
        CONFIG.read('config.ini')
        # Retrieving User information from config.ini for PRAW
        self.user = CONFIG.get('main', 'USER')
        self.password = CONFIG.get('main', 'PASSWORD')
        self.client = CONFIG.get('main', 'CLIENT_ID')
        self.secret = CONFIG.get('main', 'SECRET')
        self.subreddit = CONFIG.get('main', 'SUBREDDIT')
        self.command = CONFIG.get('main', 'COMMAND')
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

    def get_token(self):
        """Gets OAUTH access token for PRAW"""
        client_auth = requests.auth.HTTPBasicAuth(self.client, self.secret)
        post_data = {'grant_type': 'password', 'username': self.user, 'password': self.password}
        headers = {'User-Agent': self.user_agent}
        response = requests.Session()
        response2 = response.post(self.token_url, auth=client_auth, data=post_data, headers=headers)
        self.token = response2.json()['access_token']
        self.t_type = response2.json()['token_type']



    def check_comments_for_command(self, commentTree):
        """
        commentTree - CommentForest class from PRAW
        Returns true if self.command is found in the comment body
        Returns false otherwise
        """
        if type(commentTree) is CommentForest:
            for comment in commentTree:
                if self.command in comment.body:
                    return True
            return False
        else:
            print("The parameter must be of type, CommentForest")



    def main(self):
        """Main - handling running of the bot"""
        while True:
            print(f"...Searching for posts with the command, {self.command}")
            for post in self.reddit.subreddit(self.subreddit).stream.submissions(pause_after=1):
                if post is None:
                    break
                elif (post.link_flair_text == self.flair) or post.archived:
                    continue
                else:
                    print(type(post.comments))
                    comment_check = self.check_comments_for_command(post.comments)
                    if comment_check:
                        post.mod.flair(self.flair)
                        print(f"Post: {post.id} flair changed to {self.flair}")
            print(f"...Taking a small break!  Be back in {self.delay} seconds")
            time.sleep(self.delay)







if __name__ == "__main__":
    bot = DealExpiredBot()
    bot.main()



