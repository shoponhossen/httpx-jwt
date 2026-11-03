import asyncio
from pathlib import Path
import httpx
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


class AsyncAPIClient:
    def __init__(self, host: str, login_path: str, filepath: str):
        self._base_url = httpx.URL(host)
        self._silent_login_path = login_path

        self.access_token = None
        self._ts = TokenStorage(filepath)

        self._client = httpx.AsyncClient()

        self._lock = asyncio.Lock()

    async def _execute_silent_login(self) -> bool:
        """
        Attempts to refresh the access token asynchronously.
        Returns True if successful, False otherwise.
        """
        refresh_token = self._ts.get_token()
        if not refresh_token:
            return False

        url = f"{self._base_url}/{self._silent_login_path}"
        try:
            # Must await the async client request
            response = await self._client.post(url, json={"refresh": refresh_token})
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access")
                if "refresh" in data:
                    self._ts.set_token(data["refresh"])
                return True
        except httpx.HTTPError, JSONDecodeError:
            pass
        return False

    async def request(
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
                async with self._lock:
                    if not self.access_token:
                        await self._execute_silent_login()

            headers["Authorization"] = f"Bearer {self.access_token}"

        url = f"{self._base_url}/{path}"

        try:
            # Await the execution of the request
            response = await self._client.request(
                method=method, url=url, json=json, headers=headers
            )
            r_status_code = response.status_code
            r_json = response.json()
        except JSONDecodeError:
            return await on_error(content="Server returned invalid JSON content.")
        except httpx.HTTPError as e:
            return await on_error(content=f"Network error occurred: {str(e)}")

        # 1. Catch Expired Token interceptor
        if r_status_code == 401 and r_json.get("code") == "token_not_valid":
            print("[Client] Access token expired. Attempting silent login...")

            # Lock guarantees only ONE network call goes out to refresh the token
            async with self._lock:
                # If a concurrent request already updated the token while we waited, skip hitting the refresh endpoint again
                current_token_header = f"Bearer {self.access_token}"
                if headers.get("Authorization") == current_token_header:
                    login_success = await self._execute_silent_login()
                else:
                    login_success = (
                        True  # A concurrent task already successfully refreshed it!
                    )

            if login_success:
                print("[Client] Silent login successful. Retrying original request...")
                return await self.request(
                    path=path,
                    method=method,
                    on_error=on_error,
                    on_success=on_success,
                    json=json,
                    auth=auth,
                )
            else:
                print("[Client] Silent login failed.")
                return await on_error(content="Session expired. Please log in again.")

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

    async def close(self):
        # Closing an AsyncClient must be awaited
        await self._client.aclose()


# Convert your callback hooks to async def functions so they don't block the loop
def on_success(data: dict, status: int):
    print(f"Success ({status}):", data)


def on_error(content: str | dict):
    print("Error:", content)


async def main():
    c = AsyncAPIClient(
        host="http://localhost:8000/api",
        login_path="token/refresh/",
        filepath=".token",
    )

    # You can now fire requests sequentially or concurrently via asyncio.gather
    await c.request(
        path="blog/nonauth/error/",
        method="GET",
        on_error=on_error,
        on_success=on_success,
        auth=False,
    )

    await c.request(
        path="blog/auth/",
        method="POST",
        on_error=on_error,
        on_success=on_success,
    )

    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
