import pytest
from pydantic import ValidationError
import allure
from models import UserResponse, TokenResponse, HTTPValidationError, ErrorResponse

@allure.epic("Аутентификация")
@allure.feature("Вход/Логин")
class TestAuth:

    @allure.story("Регистрация пользователя с корректными данными")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка, что система может зарегистрировать пользователя с валидными данными")
    @pytest.mark.positive
    def test_register_success(self, api_client, test_user_credentials):
        import uuid

        with allure.step("Генерация данных для регистрации"):
            unique_email = f"test_{uuid.uuid4().hex[:8]}@tester.com"

            user_data = {
                "email": unique_email,
                "password": test_user_credentials["password"],
                "first_name": test_user_credentials["first_name"],
                "last_name": test_user_credentials["last_name"],
                "phone": "89991112233"
            }
        with allure.step("Отправка запроса"):
            response = api_client.post("/api/auth/register", json=user_data, expected_status = 200)

        with allure.step("Проверка ответа"):
            try:
                user = UserResponse(**response.json())
            except ValidationError:
                raise

            assert user.email == unique_email
            assert user.first_name == user_data["first_name"]
            assert user.last_name == user_data["last_name"]
            assert user.phone == user_data["phone"]
            assert user.id > 0
            assert user.created_at is not None

            api_client.user_id = user.id

    @allure.story("Регистрация уже зарегистрированного пользователя")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, что система не даст зарегистрироваться на уже зарегистрированную почту")
    @pytest.mark.negative
    def test_reregister_user(self, api_client, test_user_credentials):
        with allure.step("Формирование данных для запроса"):
            user_data = {
                "email": test_user_credentials["email"],
                "password": test_user_credentials["password"],
                "first_name": test_user_credentials["first_name"],
                "last_name": test_user_credentials["last_name"]
            }
        with allure.step("Отправка запроса"):
            response = api_client.post("/api/auth/register", json=user_data, expected_status = 400)

        with allure.step("Проверка ответа"):
            error_response = ErrorResponse(**response.json())
            assert error_response.detail == "Email already registered"

    @allure.story("Регистрация с невалидной почтой")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, что система не даст зарегистрироваться с невалидной почтой")
    @pytest.mark.negative
    def test_register_wrong_email(self, api_client, test_user_credentials):
        with allure.step("Формирование данных для запроса"):
            user_data = {
                "email": "test",
                "password": test_user_credentials["password"],
                "first_name": test_user_credentials["first_name"],
                "last_name": test_user_credentials["last_name"]
            }

        with allure.step("Отправка запроса"):
            response = api_client.post("/api/auth/register", json=user_data, expected_status = 422)

        with allure.step("Проверка ответа"):
            error = HTTPValidationError(**response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert all("value is not a valid email address" in msg for msg in messages)


    @allure.story("Регистрация с невалидным паролем")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, что система не даст зарегистрироваться с паролем длиной менее 6 символов ")
    @pytest.mark.negative
    def test_register_short_password(self, api_client, test_user_credentials):
        import uuid
        with allure.step("Формирование данных для запроса"):
            unique_email = f"test_{uuid.uuid4().hex[:8]}@tester.com"
            user_data = {
                "email": unique_email,
                "password": "pass",
                "first_name": test_user_credentials["first_name"],
                "last_name": test_user_credentials["last_name"],
            }

        with allure.step("Отправка запроса"):
            response = api_client.post("/api/auth/register", json=user_data, expected_status = 422)

        with allure.step("Проверка ответа"):
            error = HTTPValidationError(**response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert all(msg == "String should have at least 6 characters" for msg in messages)


    @allure.story("Вход пользователя с корректными данными")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка, что пользователь может зайти")
    @pytest.mark.positive
    def test_login_success(self, api_client, test_user_credentials):
        with allure.step("Формирование данных для запроса"):
            login_data = {
                "username": test_user_credentials["email"],
                "password": test_user_credentials["password"],
            }

        with allure.step("Отправка запроса"):
            login_response = api_client.post("/api/auth/login", data=login_data, expected_status = 200, headers = {"Content-Type": "application/x-www-form-urlencoded"})

        with allure.step("Проверка ответа"):
            token = TokenResponse(**login_response.json())
            assert token.access_token is not None
            assert len(token.access_token) > 20
            assert token.token_type == "bearer"

        with allure.step("Проверка данных пользователя"):
            api_client.session.headers.update({"Authorization": f"Bearer {token.access_token}"})

            user_response = api_client.get("/api/users/me", expected_status = 200)
            user = UserResponse(**user_response.json())

            assert user.email == test_user_credentials["email"]
            assert user.first_name == test_user_credentials["first_name"]
            assert user.last_name == test_user_credentials["last_name"]



    @allure.story("Вход пользователя с некорректными данными")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка, что система не даст войти с некорректными данными(пароль/почта)")
    @pytest.mark.negative
    @pytest.mark.parametrize("email, password", [(True, False), (False, True)])
    def test_login_wrong_password_email(self, api_client, test_user_credentials, email, password):
        with allure.step("Формирование данных для запроса"):
            email = test_user_credentials["email"] if email else "emailwrong"
            password = test_user_credentials["password"] if password else "passwordwrong"
            login_data = {
                "username": email,
                "password": password,
            }

        with allure.step("Отправка запроса"):
            login_response = api_client.post("/api/auth/login", data=login_data, expected_status = 401, headers = {"Content-Type": "application/x-www-form-urlencoded"})

        with allure.step("Проверка ответа"):
            error_response = ErrorResponse(**login_response.json())
            assert "Incorrect email or password" in error_response.detail

    @allure.story("Вход пользователя с пустыми данными в запросе")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка, как система среагирует на отсутствие данных для авторизации")
    @pytest.mark.negative
    @pytest.mark.parametrize("login_data", [ {}, {"username": "test@example.com"}, {"password": "password123"} ])
    def test_login_empty_fields(self, api_client, login_data):
        with allure.step("Отправка запроса"):
            login_response = api_client.post("/api/auth/login", data=login_data, expected_status = 422, headers = {"Content-Type": "application/x-www-form-urlencoded"})

        with allure.step("Проверка ответа"):
            error = HTTPValidationError(**login_response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert all(msg == "Field required" for msg in messages)
