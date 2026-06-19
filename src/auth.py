import os
import requests
import time
from dotenv import load_dotenv
from typing import Optional

load_dotenv(override=True)

class HhAuth:
    """Класс для работы с OAuth hh.ru"""

    TOKEN_URL = "https://hh.ru/oauth/token"
    _access_token: Optional[str] = None

    @classmethod
    def get_token(cls, retries: int = 1) -> str:
        if cls._access_token:
            return cls._access_token

        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")

        if not client_id or not client_secret:
            print("⚠️ CLIENT_ID / CLIENT_SECRET не найдены в .env — работаем без токена")
            return ""

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            print("🔑 Получение токена...")
            response = requests.post(cls.TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            cls._access_token = response.json()["access_token"]
            print("✅ OAuth токен успешно получен!")
            return cls._access_token

        except requests.exceptions.SSLError as e:
            print(f"❌ SSL-ошибка: {e}")
            print("💡 Попробуй отключить VPN/антивирус")

        except requests.exceptions.HTTPError as e:
            print(f"❌ Ошибка HTTP {e.response.status_code}: {e.response.json()}")

        except Exception as e:
            print(f"❌ Ошибка получения токена: {e}")

        print("⚠️ Не удалось получить токен. Продолжаем без авторизации.")
        return ""

    @classmethod
    def get_headers(cls) -> dict:
        """Возвращает headers"""
        headers = {
            "User-Agent": "JobAppCoursework/2.0 (educational project)",
        }
        token = cls.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers