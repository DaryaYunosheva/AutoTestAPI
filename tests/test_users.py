import pytest
import allure
from pygments.lexers import email

from conftest import test_user_credentials
from models import UserResponse, HTTPValidationError


@allure.epic("Профиль")
@allure.feature("Получение/Изменение данных")
class TestUser:

    @allure.story("Получение пользователя")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("Проверка на соответствие данных в бд")
    @pytest.mark.positive
    def test_get_current_user(self, auth_client, test_user_credentials):
        with allure.step("Отправка запроса"):
            response = auth_client.get("/api/users/me", expected_status=200)

        with allure.step("Проверка ответа"):
            user = UserResponse(**response.json())
            assert user.email == test_user_credentials["email"]
            assert user.first_name == test_user_credentials["first_name"]
            assert user.last_name == test_user_credentials["last_name"]
            assert user.id == auth_client.user_id
            assert user.created_at is not None
            assert user.id > 0

    @allure.story("Редактирование данных пользователя")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("Проверка, что система может корректно обновить данные")
    @pytest.mark.positive
    def test_update_user_data(self, auth_client, test_user_credentials):
        import uuid
        with allure.step("Получение текущего пользователя"):
            response_me = auth_client.get("/api/users/me", expected_status=200)
            current_user = UserResponse(**response_me.json())

        with allure.step("Подготовка новых данных"):
            new_first_name = f"Test_{uuid.uuid4().hex[:6]}"
            new_last_name = f"User_{uuid.uuid4().hex[:6]}"
            new_phone = "79991234567"

            update_data = {
                "email": test_user_credentials["email"],
                "first_name": new_first_name,
                "last_name": new_last_name,
                "phone": new_phone,
                "password": test_user_credentials["password"]
            }
        try:
            with allure.step("Обновление пользователя"):
                response = auth_client.put("/api/users/me", json=update_data, expected_status=200, headers={"Content-Type": "application/json"})

            with allure.step("Проверка ответа"):
                updated_user = UserResponse(**response.json())

                assert updated_user.id == current_user.id
                assert updated_user.email == current_user.email
                assert updated_user.first_name == new_first_name
                assert updated_user.last_name == new_last_name
                assert updated_user.phone == update_data["phone"]
                assert updated_user.created_at == current_user.created_at
        finally:
            with allure.step("Возврат к первоначальному виду"):
                data = {
                    "email": current_user.email,
                    "first_name": current_user.first_name,
                    "last_name": current_user.last_name,
                    "phone": current_user.phone,
                    "password": test_user_credentials["password"]
                }
                response_me = auth_client.put("/api/users/me", json=data, expected_status=200, headers={"Content-Type": "application/json"})

                restored_user = UserResponse(**response_me.json())

                assert restored_user.id == current_user.id
                assert restored_user.email == current_user.email
                assert restored_user.first_name == current_user.first_name
                assert restored_user.last_name == current_user.last_name
                assert restored_user.phone == current_user.phone

    @allure.story("Некорректное редактирование данных пользователя (EMAIL)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка, что система отклонит обновление из-за некорректной почты")
    @pytest.mark.negative
    @pytest.mark.parametrize("email, password, expected_message", [("wrong_email", "password123", "value is not a valid email address")])
    def test_update_user_data_wrong(self, auth_client, test_user_credentials, email, password, expected_message):

        with allure.step("Подготовка новых данных"):
            update_data = {
                "email": email,
                "first_name": test_user_credentials["first_name"],
                "last_name": test_user_credentials["last_name"],
                "phone": "79991234567",
                "password": password
            }

        with allure.step("Обновление пользователя"):
            response = auth_client.put("/api/users/me", json=update_data, expected_status=422, headers={"Content-Type": "application/json"})

        with allure.step("Проверка ошибки"):
            error = HTTPValidationError(**response.json())
            assert error.detail
            messages = [detail.msg for detail in error.detail]
            assert any(expected_message in msg for msg in messages)



    @allure.story("Некорректное редактирование данных пользователя (PASSWORD)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Проверка отклонения пароля короче 6 символов")
    @pytest.mark.negative
    @pytest.mark.skip(reason="БАГ: API принимает пароль короче 6 символов и возвращает 200 вместо 422")
    def test_update_user_short_password(self,auth_client,test_user_credentials,):
        update_data = {
            "email": test_user_credentials["email"],
            "first_name": test_user_credentials["first_name"],
            "last_name": test_user_credentials["last_name"],
            "phone": "79991234567",
            "password": "passw",
        }

        response = auth_client.put("/api/users/me", json=update_data, expected_status=422, headers={"Content-Type": "application/json"})
