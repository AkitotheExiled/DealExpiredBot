import praw
from datetime import datetime, timedelta, timezone, date
from configparser import ConfigParser
import requests
import time
import re
from src.database.database import Posts, Subreddit, Database
import logging, json

class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.FileHandler("dealexpired.log")
        self.handler.setLevel(logging.DEBUG)

        self.formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)


class RedditBaseClass:
    def __init__(self):
        CONFIG = ConfigParser()
        CONFIG.read('config.ini')
        # Retrieving User information from config.ini for PRAW
        self.user = CONFIG.get('main', 'USER')
        self.password = CONFIG.get('main', 'PASSWORD')
        self.client = CONFIG.get('main', 'CLIENT_ID')
        self.secret = CONFIG.get('main', 'SECRET')
        self.delay = CONFIG.getint('main', 'DELAY')
        self.days = CONFIG.getint('main', 'DAYS')

class DealExpiredBot(RedditBaseClass):

    def __init__(self):
        super().__init__()
        self.user_agent = "DealExpired / V1.1 / By ScoopJr"
        print('Starting up...', self.user_agent)
        self.reddit = praw.Reddit(client_id=self.client,
                                  client_secret=self.secret,
                                  password=self.password,
                                  user_agent=self.user_agent,
                                  username=self.user)
        self.subreddits = []
        self.td = timezone(-timedelta(hours=7), name="RPST")
        self.config_json = {}
        self.unixnow = datetime.timestamp(datetime.now(self.td.utc))
        self.db = Database()
        self.time_to_check = True
        self.update_old_posts = True
        self.log = Logger()
        self.logger = self.log.logger
        self.queue = {"data":[]}
        self.counter = 0


    def get_modded_subs(self):
        self.subreddits.clear()
        for subreddit in self.reddit.redditor(self.user).moderated():
            self.subreddits.append(subreddit.display_name)

    def get_wiki_json(self, sub):
        url = f"https://www.reddit.com/r/{sub}/wiki/botconfig.json"
        print(url)
        time.sleep(2)
        try:
            response = requests.get(url, headers={"User-agent": self.user_agent}).json()
            print(response)
            self.config_json[sub]["config"] = response["data"]["content_md"]
            self.config_json[sub]["config"] = self.config_json[sub]["config"].replace('\n', '')
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to get wiki json", exc_info=True)


    def get_flair_and_type(self, sub):
        if self.config_json[sub]["config"] is None:
            return f"{sub} has not setup a config page!  Skipping for now."
        if "COMMAND" in self.config_json[sub]["config"]:
            command_pat = "FLAIR=(.*)COMMAND=(.*)"
            com_compile = re.compile(command_pat)
            pat_search = com_compile.search(self.config_json[sub]["config"])
            flair = pat_search.group(1)
            print(flair)
            command = pat_search.group(2)
            self.config_json[sub]["is_command"] = True
            self.config_json[sub]["flair"] = flair
            self.config_json[sub]["command"] = command
            self.config_json[sub]["config_check"] = str(self.unixnow)
        else:
            pattern = "FLAIR=(.*)DAYS_BEFORE_FLAIRING=(\d+)"
            comp = re.compile(pattern)
            config = comp.search(self.config_json[sub]["config"])
            flair = config.group(1)
            days = config.group(2)
            self.config_json[sub]["is_command"] = False
            self.config_json[sub]["flair"] = flair
            self.config_json[sub]["days"] = int(days)
            self.config_json[sub]["config_check"] = str(self.unixnow)

    def get_or_create(self, model, subname,**kwargs):
        instance = self.db.session.query(model).filter_by(name=subname).first()
        if instance:
            return instance
        else:
            instance = model(**kwargs)
            self.db.session.add(instance)
            self.db.session.commit()

    def exist_check_or_add_posts(self, model, **kwargs):
        instance = self.db.session.query(model).filter_by(id=kwargs["post_id"]).first()
        if instance:
            return True
        else:
            instance = model(**kwargs)
            self.db.session.add(instance)
            self.db.session.commit()
            return False


    def check_for_changes(self, model, subname, **kwargs):
        instance = self.db.session.query(model).filter_by(name=subname).first()
        if instance:
            if instance.is_command != kwargs['is_command']:
                instance.is_command = kwargs['is_command']
            if instance.flair != kwargs['flair']:
                instance.flair = kwargs['flair']
            if instance.days != kwargs['days']:
                instance.days = kwargs['days']
            if instance.command != kwargs['command']:
                instance.command = kwargs['command']
            if instance.config_check != kwargs['config_check']:
                instance.config_check = kwargs['config_check']
            self.db.session.commit()
            return False
        else:
            return True

    def setup_config_json(self):
        for sub in self.subreddits:
            self.config_json[sub] = {"config": None, "is_command": None, "flair": None, "days": None,"command": None, "config_check": None}
            print(self.config_json[sub])
            self.get_wiki_json(sub)
            self.get_flair_and_type(sub)
            should_create = self.check_for_changes(Subreddit, subname=sub,name=sub, is_command=self.config_json[sub]["is_command"],flair=self.config_json[sub]["flair"], days=self.config_json[sub]["days"], command=self.config_json[sub]["command"], config_check=str(self.unixnow))
            if should_create:
                self.get_or_create(Subreddit, subname=sub,name=sub, is_command=self.config_json[sub]["is_command"],flair=self.config_json[sub]["flair"], days=self.config_json[sub]["days"], command=self.config_json[sub]["command"], config_check=str(self.unixnow))


    def delete_subs(self):
        try:
            subs = self.db.session.query(Subreddit).all()
            for sub in subs:
                if sub.name in self.subreddits:
                    continue
                else:
                    try:
                        to_delete = self.db.session.query(Subreddit).filter_by(name=sub.name).one()
                        self.db.session.delete(to_delete)
                        self.db.session.commit()
                    except Exception:
                        self.logger.error("Unable to delete subs from database", exc_info=True)

        except Exception:
            self.logger.error("Unable to query database", exc_info=True)

    def convert_utc_to_local(self, utcstamp):
        """

        utcstamp: Takes a unix timestamp and converts it to America/Los Angeles time
        :return Returns a unix timestamp that accounts for tzinfo=America/Los Angeles
        """
        timez = timezone(-timedelta(hours=7), name="RTLA") #accounting for timezone in America/Los Angeles diff
        reddit_date = datetime.utcfromtimestamp(int(utcstamp)) #turning created_utc integer into a datetime object
        timestamp = reddit_date.replace(tzinfo=timez).timestamp() #replacing tzinfo of None to the correct timezone
        return timestamp

    def get_days_between(self, utctoday, utcconverted):
        """

        :param utctoday: Takes in a datetime object that is aware, I.E. datetime.now() but accounting for Los Angeles time
        :param utcconverted: Times in a converted unix timestamp
        :return: The rounded amount of days between the two unix timestamps
        """
        if utcconverted is None:
            return
        utcconverted = int(float(utcconverted))
        return round(((utctoday - utcconverted)/(60*60*24)))



    def check_should_be_flaired(self, sub, utc):
        """

        :param utc: Takes an created_utc from Reddit and converts it to aware unix datetime object
        :return: If the days passed is greater than the limit set by the user, return True, else return False I.E. Post made 3 days ago = 3 > 14 = False
        """
        days = self.get_days_between(self.unixnow, self.convert_utc_to_local(utc))
        print(self.config_json[sub])
        if self.config_json[sub]['days'] is None:
            return
        if days >= self.config_json[sub]['days']:
            return True
        else:
            return False

    def check_post_for_command(self, sub, commentTree):
        for comment in commentTree:
            if comment.author.name == "AutoModerator":
                continue
            if self.config_json[sub]['command'] in comment.body:
                return True
        return False

    def get_config_from_database(self):
        subreddits = self.db.session.query(Subreddit.name).all()
        for sub in subreddits:
            self.config_json[sub[0]] = {"config": None, "is_command": None, "flair": None, "days": None,
                                        "command": None, "config_check": None}
            flair = self.db.session.query(Subreddit.flair).filter(Subreddit.name == sub[0]).first()
            time = self.db.session.query(Subreddit.config_check).filter(Subreddit.name == sub[0]).first()
            is_command = self.db.session.query(Subreddit.is_command).filter(Subreddit.name == sub[0]).first()
            if bool(is_command[0]):
                command = self.db.session.query(Subreddit.command).filter(Subreddit.name == sub[0]).first()
                self.config_json[sub[0]]['flair'] = flair[0]
                self.config_json[sub[0]]['is_command'] = is_command[0]
                self.config_json[sub[0]]['command'] = command[0]
                self.config_json[sub[0]]['config_check'] = int(float(time[0]))
            else:
                days = self.db.session.query(Subreddit.days).filter(Subreddit.name == sub[0]).first()
                self.config_json[sub[0]]['flair'] = flair[0]
                self.config_json[sub[0]]['days'] = days[0]
                self.config_json[sub[0]]['config_check'] = int(float(time[0]))
            self.subreddits.append(sub[0])

    def get_allposts_wpush(self, sub, before_utc, after_utc, loop=True):
        rounded_before = round(before_utc)
        rounded_after = round(after_utc)
        url = f"https://api.pushshift.io/reddit/search/submission/?subreddit={sub}&sort=desc&sort_type=created_utc&after={rounded_after}&before={rounded_before}&size=1000"
        after = None
        before = rounded_after - 10000000
        print(url)
        try:
            data = requests.get(url).json()
            print(data)
            if not data["data"]:
                self.counter = 0
                return self.queue
            if requests.get(url).status_code == requests.codes.ok:
                for items in data["data"]:
                    try:
                        if self.config_json[sub]["flair"] == items.get("link_text_flair", ""):
                            continue
                        after = items.get("created_utc", None)
                        self.queue["data"].append({"postid": items.get("id", None)})
                        self.queue["data"][self.counter]["created_utc"] = items.get("created_utc", None)
                        self.counter += 1
                    except Exception as e:
                        self.logger.info("Error getting pushshift post data", exc_info=True)
                if loop:
                    self.get_allposts_wpush(sub, after, before)
            else:
                print(self.queue)
                self.counter = 0
                return self.queue
        except Exception:
            self.logger.info("Error getting pushshift post data", exc_info=True)

    def find_flair_by_postid(self, postid):
        submission = self.reddit.submission(id=postid)
        if submission.link_flair_text:
            return submission.link_flair_text
        else:
            return None

    def flair_post_by_postid(self, postid, flair):
        submission = self.reddit.submission(id=postid)
        submission.mod.flair(flair)
    def reset_queue(self):
        self.queue = {"data":[]}
    def post_checker_by_ids(self, sub, postids):
        if not postids:
            return
        i = 0
        postIdDatabase = self.db.session.query(Posts).filter_by(subreddit_name=sub).all()
        print(postids)
        for item in postids["data"]:
            if item["postid"] in postIdDatabase:
                continue
            post_check = self.check_should_be_flaired(sub, item["created_utc"])
            if post_check:
                flair_check = self.find_flair_by_postid(item["postid"])
                if flair_check == self.config_json[sub]['flair']:
                    continue
                else:
                    self.flair_post_by_postid(item["postid"], self.config_json[sub]['flair'])
                    shouldAdd = self.exist_check_or_add_posts(Posts, post_id=item["postid"], subreddit_name=sub)
                    if shouldAdd:
                        continue
                    else:
                        print(
                            f"Sub: {sub}, Post: {item['postid']} flair changed to {self.config_json[sub]['flair']}")
                i += 1
        self.reset_queue()
    def batch_update_old_posts(self, subreddits):
        for subreddit in subreddits:
            if bool(self.config_json[subreddit]["is_command"]):
                continue
            data = self.get_allposts_wpush(subreddit,self.unixnow, self.unixnow-10000000)
            print(data)
            self.post_checker_by_ids(subreddit, self.queue)
        return "Finished batch updating old posts!"

    def subreddits_post_checker(self, subreddits):
        for subreddit in subreddits:
            if self.time_to_check:
                break
            if self.config_json[subreddit]['config_check'] is None:
                continue
            if int(float(self.days)) < self.get_days_between(self.unixnow,
                                                             self.config_json[subreddit]['config_check']):
                self.time_to_check = True
                break
            else:
                try:
                    for post in self.reddit.subreddit(subreddit).stream.submissions(pause_after=1):
                        if self.config_json[subreddit]['is_command']:
                            print(
                                f"[{subreddit}]Searching for posts with the command: {self.config_json[subreddit]['command']}")
                        else:
                            print(
                                f"[{subreddit}]Searching for posts that are older than: {self.config_json[subreddit]['days']} days...")
                        if post is None:
                            break
                        if post.stickied:
                            continue
                        if "-" in self.config_json[subreddit]['flair']:
                            if (post.link_flair_template_id == self.config_json[subreddit]['flair']):
                                continue
                        else:
                            if (post.link_flair_text == self.config_json[subreddit]['flair']):
                                continue
                        if self.config_json[subreddit]['is_command']:
                            post_check = self.check_post_for_command(subreddit, post.comments)
                            if post_check:
                                try:
                                    post.mod.flair(self.config_json[subreddit]["flair"])
                                    self.db.session.add(Posts(post_id=post.id, subreddit_name=subreddit))
                                    self.db.session.commit()
                                    print(
                                        f"Sub: {subreddit}, Post: {post.id} flair changed to {self.config_json[subreddit]['flair']}")
                                except Exception:
                                    self.time_to_check = True
                                    self.logger.info("Unable to flair posts", exc_info=True)
                                    break
                        else:
                            post_check = self.check_should_be_flaired(subreddit, post.created_utc)
                            if post_check:
                                try:
                                    post.mod.flair(self.config_json[subreddit]["flair"])
                                    self.db.session.add(Posts(post_id=post.id, subreddit_name=subreddit))
                                    self.db.session.commit()
                                    print(
                                        f"Sub: {subreddit}, Post: {post.id} flair changed to {self.config_json[subreddit]['flair']}")
                                except Exception:
                                    self.time_to_check = True
                                    self.logger.info("Unable to flair posts", exc_info=True)
                                    break
                except Exception:
                    self.logger.error("Main Loop Error", exc_info=True)

                print(f"...No new posts found! Going to next subreddit!")
                time.sleep(self.delay)

    def get_utc_days_ago(self, days):
        if days == 0:
            return self.unixnow
        past_date = datetime.now(tz=self.td) - timedelta(days)
        return datetime.timestamp(past_date)

    def check_command_subreddit_for_flair(self, subreddit):
        try:
            for post in self.reddit.subreddit(subreddit).stream.submissions(pause_after=1):
                if self.config_json[subreddit]['is_command']:
                    print(
                        f"[{subreddit}]Searching for posts with the command: {self.config_json[subreddit]['command']}")
                else:
                    print(
                        f"[{subreddit}]Searching for posts that are older than: {self.config_json[subreddit]['days']} days...")
                if post is None:
                    return
                if post.stickied:
                    continue
                if "-" in self.config_json[subreddit]['flair']:
                    if (post.link_flair_template_id == self.config_json[subreddit]['flair']):
                        continue
                else:
                    if (post.link_flair_text == self.config_json[subreddit]['flair']):
                        continue
                if self.config_json[subreddit]['is_command']:
                    post_check = self.check_post_for_command(subreddit, post.comments)
                    if post_check:
                        try:
                            post.mod.flair(self.config_json[subreddit]["flair"])
                            self.db.session.add(Posts(post_id=post.id, subreddit_name=subreddit))
                            self.db.session.commit()
                            print(
                                f"Sub: {subreddit}, Post: {post.id} flair changed to {self.config_json[subreddit]['flair']}")
                        except Exception:
                            self.time_to_check = True
                            self.logger.info("Unable to flair posts", exc_info=True)
                            return
        except Exception:
            self.logger.error("[COMMAND_CHECKER] ERROR", exc_info=True)
    def sub_post_checker(self, subreddits):
        # for loop
        for sub in subreddits:
            #days and getting data from pushshift
            # if the subreddit uses a command instead of a days passed skip
            if bool(self.config_json[sub]["is_command"]):
                self.check_command_subreddit_for_flair(sub)
                continue
            # today-days I.E. 7/15 - 30 days = 6/15
            min_days = int(self.config_json[sub]['days'])
            max_days = min_days + 1
            before_utc = self.get_utc_days_ago(min_days)
            after_utc = self.get_utc_days_ago(max_days)
            # grab posts between before and after date timeframe I.E. min = 6/15. max = 6/14 return posts from 30-31 days ago(past our minimum limit for reflairing)
            self.get_allposts_wpush(sub,before_utc,after_utc,loop=False)
            for item in self.queue["data"]:
                self.flair_post_by_postid(item["postid"], self.config_json[sub]['flair'])





    def main(self):
        """Main - handling running of the bot"""
        print("...Bot is searching for its subreddits and configurations!")
        dayInSeconds = 86400
        while True:
            if (not self.db.session.query(Subreddit).all()) or self.time_to_check:
                self.get_modded_subs()
                self.delete_subs()
                self.setup_config_json()
                self.time_to_check = False
            else:
                self.get_config_from_database()
                if False:
                    self.batch_update_old_posts(self.subreddits)
            while True:
                self.sub_post_checker(self.subreddits)
                print("Sleeping for a day.  Will run bot a day later")
                time.sleep(dayInSeconds)











if __name__ == "__main__":
    bot = DealExpiredBot()
    bot.main()



