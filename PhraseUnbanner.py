import requests
import json
import time


class PhraseUnbanner(object):
    def __init__(self):
        with open("credentials.json", "r") as credential_file:
            self._credentials = json.loads(credential_file.read())

        with open("config.json", "r") as config_file:
            self._config = json.loads(config_file.read())

        with open("data.json", "r") as data_file:
            self.read_comments = json.loads(data_file.read())

        self.token = self._get_token(self._credentials["client_id"],
                                     self._credentials["client_secret"],
                                     self._credentials["username"],
                                     self._credentials["password"])

    def _get_token(self, client_id, client_secret, username, password):
        client_auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        post_data = {
            "grant_type": "password",
            "username": username,
            "password": password
        }
        return requests.post("https://www.reddit.com/api/v1/access_token",
                             auth=client_auth,
                             data=post_data,
                             headers=self._headers(True, False)).json()

    def _headers(self, user_agent, authorization):
        headers = {}
        if user_agent:
            headers["User-Agent"] = self._credentials["user_agent"]
        if authorization:
            headers["Authorization"] = self.token["token_type"] + " " + self.token["access_token"]
        return headers

    def _get_all_listing_content(self, url, response):
        content = []
        count = 0
        is_more = False if response["data"]["after"] is None else True
        while is_more:
            count += 25
            response = requests.get("{}?count={}&after={}".format(url, count, response["data"]["after"]),
                                headers=self._headers(True, True)).json()
            content.extend(response["data"]["children"])
            is_more = False if response["data"]["after"] is None else True
        return content

    def comment_contains_phrase(self, comment):
        for phrase in self._config["unban_phrases"]:
            if ((self._config["must_match_phrase_exactly"] and comment["body"].lower() == phrase.lower())
                or (not self._config["must_match_phrase_exactly"] and phrase.lower() in comment["body"].lower())):
                return True
        return False

    def unban_user(self, username):
        post_data = {
            "name": username,
            "type": "banned"
        }
        response = requests.post("https://oauth.reddit.com/r/{}/api/unfriend".format(self._config["subreddit"]),
                                 data=post_data,
                                 headers=self._headers(True, True))

    def get_banned_users(self):
        banned = []

        url = "https://oauth.reddit.com/r/{}/about/banned".format(self._config["subreddit"])
        response = requests.get(url, headers=self._headers(True, True)).json()

        banned.extend(response["data"]["children"])
        banned.extend(self._get_all_listing_content(url, response))

        return banned

    def get_user_comments(self, username):
        comments = []

        url = "https://oauth.reddit.com/user/{}/comments".format(username)
        response = requests.get(url, headers=self._headers(True, True)).json()

        comments.extend(response["data"]["children"])
        comments.extend(self._get_all_listing_content(url, response))

        striped_comments = []
        for comment in comments:
            striped_comments.append({
                "author": comment["data"]["author"],
                "body": comment["data"]["body"],
                "id": comment["data"]["id"]
                "link_url": comment["data"]["link_url"]
            })

        return striped_comments

    def run(self):
        uptime = 0
        while True:
            print("Uptime: {}s".format(uptime))

            for banned_user in self.get_banned_users():
                for comment in self.get_user_comments(banned_user["name"]):
                    print(comment)
                    if comment["id"] in self.read_comments:
                        continue
                    self.read_comments.append(comment["id"])
                    if self.comment_contains_phrase(comment):
                        self.unban_user(comment["author"])
                        break

            with open("data.json", "w") as data_file:
                data_file.write(json.dumps(self.read_comments))

            uptime += self._config["check_rate"]
            time.sleep(self._config["check_rate"])


if __name__ == "__main__":
    PhraseUnbanner().run()
