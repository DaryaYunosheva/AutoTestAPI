import pytest
import requests
import allure
from models import UserResponse, TokenResponse
from typing import Dict


@pytest.fixture(scope="session")
def base_url() -> str:
    return "https://archiscope.ru"


@pytest.fixture(scope="session")
def test_user_credentials() -> Dict[str, str]:
    return {
        "email": "test@example.com",
        "password": "password123",
        "first_name": "Tester",
        "last_name": "Tester"
    }

@pytest.fixture(scope="session")
def api_client(base_url: str):
    class APIClient():
        def __init__(self):
            self.base_url = base_url
            self.session = requests.Session()



        def _get_headers(self):
            headers = {"Content-Type": "application/json"}
            return headers

        def _safe_headers(self, headers):
            safe_headers = headers.copy()

            if "Authorization" in safe_headers:
                safe_headers["Authorization"] = "***"

            return safe_headers

        def request(self, method: str, endpoint: str, expected_status: int = 200, **kwargs):
            url = f"{self.base_url}{endpoint}"

            if "headers" not in kwargs:
                kwargs["headers"] = self._get_headers()

            if "files" in kwargs:
                kwargs["headers"].pop("Content-Type", None)

            headers_for_allure = self._safe_headers(kwargs.get("headers", {}))

            with allure.step(f"{method} {endpoint}"):

                allure.attach(str(headers_for_allure), name="Request headers", attachment_type=allure.attachment_type.TEXT)

                if "data" in kwargs:
                    allure.attach(str(kwargs["data"]), name="Request data", attachment_type=allure.attachment_type.TEXT)

                if "json" in kwargs:
                    allure.attach(str(kwargs["json"]), name="Request JSON", attachment_type=allure.attachment_type.JSON)

                response = self.session.request(method, url, **kwargs)


                allure.attach(str(response.status_code), name="Response status", attachment_type=allure.attachment_type.TEXT)


                allure.attach(str(dict(response.headers)), name="Response headers", attachment_type=allure.attachment_type.TEXT)

                try:
                    response_body = response.json()

                    allure.attach(str(response_body), name="Response body", attachment_type=allure.attachment_type.JSON)

                except ValueError:
                    allure.attach(response.text, name="Response body",attachment_type=allure.attachment_type.TEXT)

                assert response.status_code == expected_status, f"При запросе {url} ожидали статус {expected_status}, получили {response.status_code}"

            return response

        def get(self, endpoint: str, expected_status: int, **kwargs):
            return self.request("GET", endpoint, expected_status, **kwargs)

        def post(self, endpoint: str, expected_status: int, **kwargs):
            return self.request("POST", endpoint, expected_status, **kwargs)

        def put(self, endpoint: str, expected_status: int = 200, **kwargs):
            return self.request("PUT", endpoint, expected_status, **kwargs)

    return APIClient()


@pytest.fixture(scope="function")
def auth_client(api_client, test_user_credentials: Dict[str, str]):
    login_data = {
        "username": test_user_credentials["email"],
        "password": test_user_credentials["password"]
    }

    with allure.step("Авторизация пользователя"):
        response = api_client.post("/api/auth/login", data=login_data, expected_status=200, headers={"Content-Type": "application/x-www-form-urlencoded"})

        token_data = TokenResponse(**response.json())

        api_client.session.headers.update({"Authorization": f"Bearer {token_data.access_token}"})

    with allure.step("Получение текущего пользователя"):
        user_response = api_client.get("/api/users/me", expected_status=200)
        user_data = UserResponse(**user_response.json())
        api_client.user_id = user_data.id

    yield api_client

    with allure.step("Возврат к неавторизованному состоянию"):
        api_client.session.headers.pop("Authorization", None)
        api_client.user_id = None
