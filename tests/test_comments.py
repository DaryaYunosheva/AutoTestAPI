from models import NewsResponse, CommentResponse, HTTPValidationError, ErrorResponse
from helpers.data_generator import generate_comment
import pytest
import allure

@allure.epic("Комментарии")
@allure.feature("Создание/получение")
class TestComments:

    @allure.story("Создание комментария с корректными данными")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка, что пользователь может зарегистрироваться с валидными данными")
    @pytest.mark.positive
    def test_new_comment_success(self, auth_client):
        with allure.step("Получение новости, для которой будет создаваться комментарий"):
            before_news_response = auth_client.get("/api/news/", expected_status=200)
            before_news = before_news_response.json()["items"]
            before_new = NewsResponse(**before_news[0])

            comments_count_new = before_new.comments_count

        with allure.step("Генерация комментария"):
            data_for_comment = generate_comment()

        with allure.step("Отправка запроса"):
            comment_response = auth_client.post(f"/api/news/{before_new.id}/comments", json = data_for_comment, headers={"Content-Type": "application/json"}, expected_status=200)

        with allure.step("Проверка ответа"):
            comment = CommentResponse(**comment_response.json())

            response = auth_client.get(f"/api/news/{before_new.id}", expected_status=200)
            news = NewsResponse(**response.json())

            assert comment.text == data_for_comment["text"]
            assert news.comments_count == comments_count_new+1

    @allure.story("Создание комментария с пустым полем")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, как система отреагирует на некорректный запрос")
    @pytest.mark.negative
    def test_new_comment_wrong(self, auth_client):
        with allure.step("Получение новости, для которой будет создаваться комментарий"):
            news_response = auth_client.get("/api/news/", expected_status=200)
            news = news_response.json()["items"]
            new = NewsResponse(**news[0])

        with allure.step("Отправка запроса"):
            response = auth_client.post(f"/api/news/{new.id}/comments", json ={}, headers={"Content-Type": "application/json"}, expected_status=422)

        with allure.step("Проверка ответа"):
            error = HTTPValidationError(**response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert all("Field required" in msg for msg in messages)

    @allure.story("Создание комментария, состоящий только из пробелов")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, что система не даст создать комментарий, состоящий из пробелов")
    @pytest.mark.negative
    @pytest.mark.xfail (reason="API принимает комментарий, состоящий только из пробелов")
    def test_new_comment_space(self, auth_client):

        with allure.step("Получение новости, для которой будет создаваться комментарий"):
            news_response = auth_client.get("/api/news/", expected_status=200)
            news = news_response.json()["items"]
            new = NewsResponse(**news[0])

        with allure.step("Формирование данных для запроса"):
            comment_data = {"text": "     "}
            response = auth_client.post(f"/api/news/{new.id}/comments", json =comment_data, headers={"Content-Type": "application/json"}, expected_status=422)

        with allure.step("Проверка ответа"):
            error = HTTPValidationError(**response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert all("Field required" in msg for msg in messages), "Комментарий не должен состоять только из пробелов"


    @allure.story("Создание комментария у неавторизованного пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, что система не даст создать комментарий без авторизации")
    @pytest.mark.negative
    def test_new_comment_not_auth(self, api_client):
        with allure.step("Получение новости, для которой будет создаваться комментарий"):
            news_response = api_client.get("/api/news/", expected_status=200)
            news = news_response.json()["items"]
            new = NewsResponse(**news[0])

        with allure.step("Генерация комментария"):
            comment_data = generate_comment()

        with allure.step("Отправка запроса"):
            response = api_client.post(f"/api/news/{new.id}/comments", json=comment_data, headers={"Content-Type": "application/json"}, expected_status=401)

        with allure.step("Проверка ответа"):
            error = ErrorResponse(**response.json())
            assert "Not authenticated" in str(error), "Комментарий нельзя создавать неавторизованному пользователю"

    @allure.story("Создание комментария с некорректным токеном")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, как система среагирует на запрос создания комментария c некорректным токеном")
    @pytest.mark.negative
    def test_create_comment_invalid_token(self, api_client):
        with allure.step("Установка некорректного токена"):
            api_client.session.headers.update({"Authorization": "Bearer invalid_token"})

        with allure.step("Получение новости, для которой будет создаваться комментарий"):
            news_response = api_client.get("/api/news/", expected_status=200)
            news = news_response.json()["items"]
            new = NewsResponse(**news[0])

        with allure.step("Генерация комментария"):
            comment_data = generate_comment()

        with allure.step("Отправка запроса"):
            response = api_client.post(f"/api/news/{new.id}/comments", json=comment_data, headers={"Content-Type": "application/json"}, expected_status=401)

        with allure.step("Проверка ответа"):
            error = ErrorResponse(**response.json())
            assert "could not validate credentials" in error.detail.lower()
        api_client.session.headers.pop("Authorization", None)

    @allure.story("Получение комментариев конкретной новости")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, что система выведет все комментарии конкретной новости")
    @pytest.mark.positive
    def test_get_comments_success(self, auth_client):
        count_com = 10
        with allure.step("Получение новости"):
            news_response = auth_client.get("/api/news/", expected_status=200)
            news = news_response.json()["items"]
            new = NewsResponse(**news[0])
            count_comments_new = new.comments_count
        created_comments_id = []

        with allure.step("Генерация комментариев"):
            for _ in range(count_com):
                data_for_comment = generate_comment()
                comment_response = auth_client.post(f"/api/news/{new.id}/comments", json = data_for_comment, headers={"Content-Type": "application/json"}, expected_status=200)
                comment = CommentResponse(**comment_response.json())
                assert comment.text == data_for_comment["text"]
                created_comments_id.append(comment.id)

        with allure.step("Отправка запроса"):
            comments_response = auth_client.get(f"/api/news/{new.id}/comments", expected_status=200)

        with allure.step("Получение ответа, проверка наличия всех сгенерированных комментариев"):
            comments = comments_response.json()
            assert len(comments) == count_com+count_comments_new
            returned_comments_id = []
            for comment in comments:
                com = CommentResponse(**comment)
                returned_comments_id.append(com.id)
            assert set(created_comments_id).issubset(returned_comments_id)

    @allure.story("Получение комментариев несуществующей новости")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, что система выведет ошибку при запросе")
    @pytest.mark.negative
    @pytest.mark.parametrize("id", [-1, 0, 100000000])
    def test_get_comment_wrong_id(self, auth_client, id):
        with allure.step("Отправка запроса"):
            comments_response = auth_client.get(f"/api/news/{id}/comments", expected_status=404)
        with allure.step("Проверка ответа"):
            error = ErrorResponse(**comments_response.json())
            assert error.detail == "News not found"

