from datetime import datetime
import requests
import random
import praw
import json
import time
import re
import os


class PhraseUnbanner(object):
    def __init__(self, config_filepath, credentials_filepath):
        with open(credentials_filepath, "r") as credential_file:
            self._credentials = json.loads(credential_file.read())

        with open(config_filepath, "r") as config_file:
            self._config = json.loads(config_file.read())

        with open("data.json", "r") as data_file:
            self.read_comments = json.loads(data_file.read())

        self.reddit = praw.Reddit(user_agent=self._credentials["user_agent"])
        self.reddit.login(self._credentials["username"], self._credentials["password"])

        self.subreddit = self.reddit.get_subreddit("Rascal_Two")

    def should_unban(self, comment):
        for phrase in self._config["unban_phrases"]:
            if ((self._config["must_be_exact"] and comment.body.lower() == phrase)
                or (not self._config["must_be_exact"] and phrase in comment.body.lower())):
                return True
        return False

    def start(self):
        while True:
            for comment in praw.helpers.comment_stream(self.reddit, "Rascal_Two"):
                if self.should_unban(comment):
                    self.subreddit.remove_ban(comment.author)
            time.sleep(15)


if __name__ == "__main__":
    PhraseUnbanner("config.json", "credentials.json").start()
