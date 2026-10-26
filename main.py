import httpx
from pathlib import Path
import json as jsonlib
from time import sleep


class Error(Exception):
    pass


class TokenStorage:
    def __init__(self, filepath: str):
        self.path = Path(filepath)

        if not self.path.exists():
            with open(self.path, "w") as f:
                f.write("")

    def set_token(self, token: str):
        with open(self.path, "w") as f:
            f.write(token)
            return True

    def get_token(self):
        with open(self.path, "r") as f:
            return f.read()


class APIClient:
    def __init__(self, host: str, login_path: str, filepath: str):
        self._base_url = httpx.URL(host)
        self._silent_login_path = login_path

        self.access_token = None
        self._ts = TokenStorage(filepath)

        self._client = httpx.Client()


    def on_silent_login(self, json, status):
        print(status, json)


    def request(self, path, method, json=None, callback=None):
        while True:
            try:
                if method == "GET":
                    r = self._client.get(
                        url=f"{self._base_url}{path}",
                        headers={"Authorization": f"Bearer {self.access_token}"},
                    )

                elif method == "POST":
                    r = self._client.post()

                else:
                    raise Error("Invalid request method.")

                print(r.content)

                try:
                    json_content: dict = r.json()

                except jsonlib.decoder.JSONDecodeError:
                    raise Error("Server return invalid json content.")

                if "Token is invalid" in str(json_content):
                    print("Access token expired.")
                    if not self._ts.get_token():
                        raise Error("There aren't any saved refresh token.")

                    self.request(
                        path=self._silent_login_path,
                        method="GET",
                        json={"refresh": self._ts.get_token()},
                        callback=self.on_silent_login,
                    )
                    sleep(1)
                    continue

                if callback:
                    callback(json=json_content, status=r.status_code)

                break

            except Error as error:
                callback(
                    json={"error": {"detail": str(error)}},
                    status=0,
                )
                break

            except Exception as e:
                # raise e

                callback(
                    json={"error": {"detail": str(e)}},
                    status=0,
                )
                break

    def close(self):
        self._client.close()


def hello(json: dict, status: int):
    print(status, json)


if __name__ == "__main__":
    c = APIClient(
        host="http://192.168.110.2:8000/api/",
        login_path="login/silent/",
        filepath=".token",
    )

    c.request(path="account/profile/", method="GET", callback=hello)
