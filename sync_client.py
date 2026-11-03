import httpx
from pathlib import Path
from json.decoder import JSONDecodeError


class TokenStorage:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        if not self.path.exists():
            self.path.touch()

    def set_token(self, token: str):
        self.path.write_text(token)
        return True

    def get_token(self) -> str:
        return self.path.read_text().strip()


class APIClient:
    def __init__(self, host: str, login_path: str, filepath: str):
        self._base_url = httpx.URL(host)
        self._silent_login_path = login_path

        self.access_token = None
        self._ts = TokenStorage(filepath)
        self._client = httpx.Client()

    def _execute_silent_login(self) -> bool:
        """
        Attempts to refresh the access token synchronously.
        Returns True if successful, False otherwise.
        """
        refresh_token = self._ts.get_token()
        if not refresh_token:
            return False

        url = f"{self._base_url}/{self._silent_login_path}"
        try:
            response = self._client.post(url, json={"refresh": refresh_token})
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access")
                # If your backend rotates refresh tokens, update it here
                if "refresh" in data:
                    self._ts.set_token(data["refresh"])
                return True
        except httpx.HTTPError, JSONDecodeError:
            pass
        return False

    def request(
        self,
        path: str,
        method: str,
        on_error,
        on_success=None,
        json=None,
        auth: bool = True,
    ):
        if json is None:
            json = {}

        headers = {}
        if auth:
            if not self.access_token:
                self._execute_silent_login()
            headers["Authorization"] = f"Bearer {self.access_token}"

        url = f"{self._base_url}/{path}"

        try:
            response = self._client.request(
                method=method, url=url, json=json, headers=headers
            )
            r_status_code = response.status_code
            r_json = response.json()
        except JSONDecodeError:
            return on_error(content="Server returned invalid JSON content.")
        except httpx.HTTPError as e:
            return on_error(content=f"Network error occurred: {str(e)}")

        # 1. Catch Expired Token interceptor
        if r_status_code == 401 and r_json.get("code") == "token_not_valid":
            print("[Client] Access token expired. Attempting silent login...")
            login_success = self._execute_silent_login()

            if login_success:
                print("[Client] Silent login successful. Retrying original request...")
                # Re-run the request with the new active token and return early to halt the broken branch
                return self.request(
                    path=path,
                    method=method,
                    on_error=on_error,
                    on_success=on_success,
                    json=json,
                    auth=auth,
                )
            else:
                print("[Client] Silent login failed.")
                return on_error(content="Session expired. Please log in again.")

        # 2. Handle standard HTTP status loops
        if 200 <= r_status_code <= 299:
            if on_success:
                on_success(data=r_json, status=r_status_code)
        elif 400 <= r_status_code <= 499:
            detail = r_json.get("detail")
            on_error(content=detail if detail else r_json)
        elif 500 <= r_status_code <= 599:
            on_error(content="Internal server error occurred.")
        else:
            on_error(content="Server returned unexpected status code.")

    def close(self):
        self._client.close()


# Test
if __name__ == "__main__":

    def on_success(data: dict, status: int):
        print(f"Success ({status}):", data)

    def on_error(content: str | dict):
        print("Error:", content)

    c = APIClient(
        host="http://localhost:8000/api",
        login_path="token/refresh/",
        filepath=".token",
    )

    c.request(
        path="blog/nonauth/error/",
        method="GET",
        on_error=on_error,
        on_success=on_success,
        auth=False,
    )
    c.request(
        path="blog/auth/",
        method="POST",
        on_error=on_error,
        on_success=on_success,
    )

    c.close()
