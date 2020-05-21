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
                                      user_agent = "scortino")
        else:
            self.reddit = praw.Reddit(bot)
        self.logger.info("Instantiated Reddit client")

        with open(bot_config, 'r') as f:
            # Store configuration parameters
            self.blocked_users, self.subreddits, self.triggers, self.quotes = json.load(f).values()

        self.subreddits = '+'.join(self.subreddits)

        # Store posts already replied to
        self.posts_replied_to_path = posts_replied_to_path
        self.posts_replied_to = self.get_post_replied_to(posts_replied_to_path)
        print(self.posts_replied_to)
    
    def start(self):
        while True:
            try:
                # Get the replies from the subreddits
                subreddit = self.reddit.subreddit(self.subreddits)

                # Iterate over comments
                for comment in subreddit.stream.comments():

                    # Check if author name exists or not
                    username = self.get_username(comment.author)
                    
                    # If we haven't replied to this comment before and the comment author is not blocked
                    if comment.id not in self.posts_replied_to and username not in self.blocked_users:
                        
                        if self.is_keyword_mentioned(comment.body):

                            # Reply to the post and write activity to the log
                            comment.reply(random.choice(self.quotes))
                            self.logger.info(f'Replied to comment in subreddit {comment.subreddit}')

                            # Store the current id into our list
                            self.posts_replied_to.append(comment.id)
                            print(self.posts_replied_to)
                            self.logger.info('Appended replied posts to list')

                            with open(self.posts_replied_to_path, 'a') as f:
                                f.write(comment.id + '\n')
                            self.logger.info(f'Written to {self.posts_replied_to_path} file, ID {comment.id}')

            except KeyboardInterrupt:
                self.logger.error('Keyboard termination received. Bye!')
                break
            except (PrawcoreException, RedditAPIException) as e:
                self.logger.exception(f'PRAW Exception received: {vars(e)}. Retrying...')
                if e.items[0].error_type == 'RATELIMIT':
                    search = re.search('minutes', str(e))
                    try:
                        seconds = (int(str(e)[search.start() - 2]) + 1) * 60
                        time.sleep(seconds)
                    except:
                        time.sleep(60)
                else:
                    time.sleep(2) # sleep to retry in case of errors

    def get_post_replied_to(self, path=None):
         # Read the file into a list and remove any empty values
        if path is None:
            f = open('./posts_replied_to.txt', 'w') if path is None else open(path, 'r')
            self.posts_replied_to_path = './posts_replied_to.txt'
            posts_replied_to = []
        else:
            f = open(path, 'r')
            posts_replied_to = list(filter(None, f.read().splitlines()))
        self.logger.info("Got posts that were already replied")
        f.close()
        return posts_replied_to

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
