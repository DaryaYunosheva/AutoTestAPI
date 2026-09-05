from random import randint

import pytest
import allure
from conftest import api_client, auth_client
from helpers.data_generator import generate_news
from models import HTTPValidationError, ErrorResponse, NewsResponse, NewsListResponse, TagResponse


@allure.epic("Новости")
@allure.feature("Создание/получение")
class TestNews:

    @allure.story("Создание новости с корректными данными")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка, что система создаст новость с валидными данными")
    @pytest.mark.positive
    @pytest.mark.parametrize("photo", [True, False])
    def test_create_news_success(self, auth_client, photo):
        headers = {"Content-Type": "multipart/form-data"}
        expected_status = 200
        with allure.step("Генерация новости"):
            data_news = generate_news()

        with allure.step("Отправка запроса"):
            if photo:
                with open("helpers/news.jpg", "rb") as image:
                    files = {"image": ("news.jpg", image, "image/jpeg")}
                    response = auth_client.post("/api/news/", data=data_news, files=files, expected_status=expected_status,headers=headers)
            else:
                response = auth_client.post("/api/news/", data = data_news, files = {}, expected_status = expected_status, headers = headers)

        with allure.step("Проверка ответа"):
            news = NewsResponse(**response.json())

            assert news.title == data_news["title"]
            assert news.subtitle == data_news["subtitle"]
            assert news.text == data_news["text"]
            assert all(tag.name in data_news["tags"] for tag in news.tags)
            assert auth_client.user_id == news.author.id
            if photo:
                assert news.image_path is not None

    @allure.story("Создание новости с пустыми полями")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, как система среагирует при некорректном запросе на создание новости")
    @pytest.mark.negative
    def test_create_news_empty(self, auth_client):
        with allure.step("Отправка запроса"):
            response = auth_client.post("/api/news/", data ={}, files = {}, expected_status = 422, headers = {"Content-Type": "multipart/form-data"})

        with allure.step("Проверка ответа"):
            error = HTTPValidationError(**response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert all("Field required" in msg for msg in messages)

    @allure.story("Создание новости у неавторизованного пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, как система среагирует на запрос создания новости без авторизации")
    @pytest.mark.negative
    def test_create_news_not_auth(self, api_client):
        with allure.step("Генерация новости"):
            data_news = generate_news()
        with allure.step("Отправка запроса"):
            response = api_client.post("/api/news/", data = data_news, files = {}, expected_status = 401, headers = {"Content-Type": "multipart/form-data"})
        with allure.step("Проверка ответа"):
            error = ErrorResponse(**response.json())
            assert "Not authenticated" in str(error)

    @allure.story("Создание новости с некорректным токеном")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, как система среагирует на запрос создания новости c некорректным токеном")
    @pytest.mark.negative
    def test_create_news_invalid_token(self, api_client):
        with allure.step("Установка некорректного токена"):
            api_client.session.headers.update({"Authorization": "Bearer invalid_token"})

        with allure.step("Отправка запроса"):
            response = api_client.post("/api/news/", data=generate_news(), expected_status=401)

        with allure.step("Проверка ответа"):
            error = ErrorResponse(**response.json())
            assert "could not validate credentials" in error.detail.lower()
        api_client.session.headers.pop("Authorization", None)

    @allure.story("Получение всех новостей")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка всех новостей")
    @pytest.mark.positive
    def test_get_news(self, api_client):
        with allure.step("Отправка запроса"):
            get_response = api_client.get("/api/news/", expected_status = 200)

        with allure.step("Проверка ответа"):
            news_response = NewsListResponse(**get_response.json())

            assert news_response.total >= 0
            assert news_response.page >= 1
            assert news_response.per_page >= 1
            assert news_response.total_pages >= 0

            news = get_response.json()["items"]
            assert all(NewsResponse(**item) for item in news)


    @allure.story("Фильтрация новостей с корректными/некорректными данными")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, как система среагирует на запрос получения новостей по корректным/некорректным фильтрам")
    @pytest.mark.negative
    @pytest.mark.positive
    @pytest.mark.parametrize("page, per_page, expected_status", [ (0, 1, 422),
                                                                (1, 0, 422),
                                                                (1, 1, 200),
                                                                (1, 50, 200),
                                                                (1, 51, 422),
                                                                (2.4, 2, 422),
                                                                (2, 2.5, 422),
                                                                ("str", 1, 422),
                                                                (1, "str", 422)])
    def test_get_news_filters_page(self, api_client,page, per_page, expected_status):
        with allure.step("Отправка запроса"):
            get_response = api_client.get("/api/news/", expected_status = expected_status, params = {"page": page, "per_page": per_page})
        with allure.step("Проверка ответа"):
            if expected_status == 422:
                error = HTTPValidationError(**get_response.json())
                assert error.detail
                messages = [detail.msg for detail in error.detail]
                assert ( any("Input should be a valid integer" in msg for msg in messages)
                    or any("Input should be less than or equal to 50" in msg for msg in messages)
                    or any("Input should be greater than or equal to 1" in msg for msg in messages))
            else:
                response = NewsListResponse(**get_response.json())
                assert response.page == page
                assert response.per_page == per_page
                assert len(response.items) <= per_page

    @allure.story("Поиск новости по слову")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, как система выведет новости с определенным словом")
    @pytest.mark.positive
    def test_get_news_filters_search(self, auth_client):
        import uuid
        with allure.step("Генерация слова и новости"):
            search_word = f"search_{uuid.uuid4().hex[:8]}"
            news_data = generate_news()
            news_data["title"] = f"News {search_word}"

        with allure.step("Создание новости"):
            auth_client.post("/api/news/", data=news_data, files = {},  expected_status = 200, headers = {"Content-Type": "multipart/form-data"})

        with allure.step("Отправка запроса"):
            get_response = auth_client.get("/api/news/", expected_status = 200, params = {"search" : search_word})

        with allure.step("Проверка ответа"):
            news = NewsListResponse(**get_response.json())
            assert news.items
            assert all(search_word.lower() in str(item).lower() for item in news.items)


    @allure.story("Поиск новости по тегу")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, как система выведет новости по тегу")
    @pytest.mark.positive
    @pytest.mark.flaky(reruns=3)
    def test_get_news_filters_tag(self, auth_client):
        with allure.step("Получение тега"):
            response_tag = auth_client.get("/api/news/tags", expected_status=200)
            tag = TagResponse(**response_tag.json()[randint(0,len(response_tag.json())-1)])


        with allure.step("Отправка запроса"):
            get_response = auth_client.get("/api/news/", expected_status=200, params={"tag": tag.name})

        with allure.step("Проверка ответа"):
            news = NewsListResponse(**get_response.json())
            assert news.items
            assert all((tag.name).lower() in str(item.tags).lower() for item in news.items)


    @allure.story("Получение новости по id")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, что система выведет нужную новость по id")
    @pytest.mark.positive
    def test_get_news_by_id_positive(self, api_client):
        with allure.step("Получение всех новостей"):
            news_response = api_client.get("/api/news/", expected_status = 200)
            news = news_response.json()["items"]
            new = NewsResponse(**news[0])

        with allure.step("Отправка запроса"):
            get_response = api_client.get(f"/api/news/{new.id}", expected_status = 200)

        with allure.step("Проверка ответа"):
            response = NewsResponse(**get_response.json())
            assert response.id == new.id
            assert response.text == new.text
            assert response.title == new.title
            assert response.author == new.author


    @allure.story("Получение новости по несуществующему id")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, что система выведет ошибку на некорректный id")
    @pytest.mark.negative
    @pytest.mark.parametrize("id, expected_status", [(0, 404),
                                                     (100000000000, 404),
                                                     (3.4, 422),
                                                     ("str", 422)])
    def test_get_news_by_id_negative(self, api_client, id, expected_status):

        with allure.step("Отправка запроса"):
            get_response = api_client.get(f"/api/news/{id}", expected_status = expected_status)

        with allure.step("Проверка ответа"):
            if expected_status == 422:
                error = HTTPValidationError(**get_response.json())
                assert error.detail
                messages = [detail.msg for detail in error.detail]
                assert all("Input should be a valid integer" in msg for msg in messages)

            if expected_status == 404:
                error = ErrorResponse(**get_response.json())
                assert "News not found" in str(error)

    @allure.story("Получение всех тегов")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, что система выведет все теги")
    @pytest.mark.positive
    def test_get_news_tags(self, api_client):
        with allure.step("Отправка запроса"):
            get_response = api_client.get("/api/news/tags", expected_status = 200)

        with allure.step("Проверка ответа"):
            tags = [TagResponse(**item) for item in get_response.json()]

            assert tags

            #assert all(tag.name.strip() for tag in tags), "Тег не должен быть пустым или состоять только из пробелов"
            assert all(tag.id > 0 for tag in tags)

            tag_ids = [tag.id for tag in tags]
            tag_names = [tag.name for tag in tags]
            assert len(tag_ids) == len(set(tag_ids))
            assert len(tag_names) == len(set(tag_names))






