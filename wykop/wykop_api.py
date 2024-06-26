from urllib.parse import urljoin
import httpx
from typing import Any, Dict, List, Optional, Literal, Union
from loguru import logger
from .models import Rank, User, Photo, Media, Votes, WykopItem, WykopLink, WykopEntry
from pydantic import parse_obj_as


class WykopAPI:
    """
    A Python client for interacting with the Wykop API.

    This class provides methods to authenticate with the Wykop API and make requests to it.

    Attributes:
    app_key (str): The application key provided by Wykop.
    secret (str): The secret key provided by Wykop.
    base_url (str, optional): The base URL for the Wykop API. Defaults to "https://wykop.pl/api/v3".
    token (str, optional): The access token obtained after successful `self.authenticate`. Defaults to None.
    """

    def __init__(
        self, app_key: str, secret: str, base_url: str = "https://wykop.pl/api/v3"
    ) -> None:
        self.app_key = app_key.strip()
        self.secret = secret.strip()
        self.base_url = base_url
        self.token: Optional[str] = None
        self.client = httpx.Client()

    def authenticate(self) -> str:
        """Authenticate with the Wykop API to get a JWT token."""
        url = f"{self.base_url}/auth"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        data = {"data": {"key": self.app_key, "secret": self.secret}}
        response = self.client.post(url, json=data, headers=headers)
        response_data = response.json()
        if response.status_code == 200:
            self.token = response_data["data"]["token"]
        else:
            raise Exception(
                f"Failed to authenticate: {response.status_code} - {response.text}"
            )
        logger.debug(f"Authenticated successfully.")
        return self.token

    def get_entries_by_tag(
        self,
        tag_name: str,
        page: int = 1,
        limit: int = 25,
        sort: Literal["all", "best"] = "best",
        type: Literal["all", "author", "link", "entry"] = "all",
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[WykopItem]:
        """Fetch entries by tag with optional pagination and filtering.
        Args:
            tag_name (str): The name of the tag to filter by.
            page (int, optional): Page number of the results to fetch. Defaults to 1.
            limit (int, optional): The number of entries per page. Defaults to 25.
            sort (str, optional): The sorting method ('all', 'best'). Defaults to 'best'.
            type (str, optional): The type of entries ('all', 'author', 'link', 'entry'). Defaults to 'all'.
            year (int, optional): The year for filtering entries.
            month (int, optional): The month for filtering entries.
        """
        endpoint = f"/tags/{tag_name}/stream"
        params = {"page": page, "limit": limit, "sort": sort, "type": type}
        if year:
            params["year"] = year
        if month:
            params["month"] = month

        response = self.make_request(endpoint, method="GET", params=params)
        entries = []
        for entry_data in response["data"]:
            if entry_data.get("description"):
                entries.append(parse_obj_as(WykopLink, entry_data))
            else:
                entries.append(parse_obj_as(WykopEntry, entry_data))
        return entries

    def make_request(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a request to a specific endpoint using the authenticated token and any HTTP method.
        List of valid endpoints: Wykop API documentation: https://doc.wykop.pl/
        """
        if not self.token:
            raise Exception(
                "You must authenticate first (call the `authenticate()` method)"
            )
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request to {url}")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        http_methods = {
            "GET": self.client.get,
            "POST": self.client.post,
            "PUT": self.client.put,
            "DELETE": self.client.delete,
            "PATCH": self.client.patch,
        }

        method = method.upper()
        if method in http_methods:
            if method == "GET" or method == "DELETE":
                response = http_methods[method](
                    url, headers=headers, params=params, follow_redirects=True
                )
            else:
                response = http_methods[method](
                    url, headers=headers, json=data, follow_redirects=True
                )
        else:
            raise ValueError("Unsupported HTTP method")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


# Example Usage
def main():
    app_key = "a"
    secret = "a"
    api = WykopAPI(app_key, secret)
    try:
        token = api.authenticate()
        print("Authenticated. Token:", token)
        response = api.make_request("/tags/popular-user-tags", data={"key": "value"})
        print(response)
    finally:
        api.close()


if __name__ == "__main__":
    main()
