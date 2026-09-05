import pytest
import allure
import requests
from unittest.mock import patch
from models import ErrorResponse


@allure.epic("Мок-тесты")
@allure.feature("Сетевые сбои")
class TestMock:

    @allure.story("Сервис недоступен 503")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_news_list_503(self, api_client):
        with allure.step("Подготовка мока"):
            mocked = requests.Response()
            mocked.status_code = 503
            mocked._content = b'{"detail":"Service temporarily unavailable"}'
        with allure.step("Подмена на мок"):
            with patch.object(api_client, "request", return_value=mocked):
                with allure.step("Отправка запроса"):
                    response = api_client.get("/api/news/", expected_status = 503, headers = {"content-type": "application/json"})
                    with allure.step("Проверка ответа"):
                        error = ErrorResponse(**response.json())
                        assert error.detail == "Service temporarily unavailable"
