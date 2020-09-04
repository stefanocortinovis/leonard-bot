import json
import os
import random
import re
import time

import logging
from logging.config import fileConfig

import praw
from prawcore.exceptions import PrawcoreException
from praw.exceptions import RedditAPIException


class RedditBot():
    def __init__(self, bot=None, logger_config='./logging_config.ini', bot_config='./bot_config.json', posts_replied_to_path=None):
        # Create logger in accordance with config file
        fileConfig(logger_config)
        self.logger = logging.getLogger('reddit')

        # Create Reddit instance
        if bot is None:
            self.reddit = praw.Reddit(username = os.environ['reddit_username'],
                                      password = os.environ['reddit_password'],
                                      client_id = os.environ["client_id"],
                                      client_secret = os.environ["client_secret"],
                                      user_agent = os.environ["user_agent"])
        else:
            # requires praw.ini to be in current dir
            self.reddit = praw.Reddit(bot)
        self.logger.info("Instantiated Reddit client")

        with open(bot_config, 'r') as f:
            # Store configuration parameters
            self.blocked_users, self.subreddits, self.triggers, self.quotes = json.load(f).values()

        self.subreddits = '+'.join(self.subreddits)
    
    def start(self):
        while True:
            try:
                # Get the replies from the subreddits
                subreddit = self.reddit.subreddit(self.subreddits)

                # Iterate over comments
                for comment in subreddit.stream.comments(skip_existing=True):

                    # Check if author name exists or not
                    username = self.get_username(comment.author)
                    
                    # Reply only if keyword mentioned and author is not blocked
                    if self.is_keyword_mentioned(comment.body) and username not in self.blocked_users:
                        # Reply to the post and write activity to the log
                        comment.reply(random.choice(self.quotes))
                        self.logger.info(f'Replied to comment in subreddit {comment.subreddit}, ID {comment.id}')

            except KeyboardInterrupt:
                self.logger.error('Keyboard termination received. Bye!')
                break
            except PrawcoreException as e:
                self.logger.exception(f'Prawcore Exception received: {vars(e)}. Retrying...')
                time.sleep(2) # sleep to retry in case of errors
            except RedditAPIException as e:
                self.logger.exception(f'Praw Exception received: {vars(e)}. Retrying...')
                if e.items[0].error_type == 'RATELIMIT':
                    search = re.search('minutes', str(e))
                    try:
                        seconds = (int(str(e)[search.start() - 2]) + 1) * 60
                        time.sleep(seconds)
                    except:
                        time.sleep(60)

    def get_username(self, author):
        name = author.name if author else '[deleted]'
        return name

    def is_keyword_mentioned(self, text):
        for trigger in self.triggers:
            # Case insensitive search
            if re.search(trigger, text, re.IGNORECASE):
                return True
        return False


if __name__ == '__main__':
    bot = RedditBot()
    bot.logger.info('Started Reddit bot')
    bot.start()
