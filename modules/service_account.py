import asyncio
import base64
import json
from datetime import datetime, timedelta

import aiohttp
from playwright.async_api import async_playwright
from config import settings


async def get_service_access_token():
    login = settings.SERVICE_ACCOUNT_LOGIN
    password = settings.SERVICE_ACCOUNT_PASSWORD

    # Проверка живой ли еще токен
    with open("data/auth_token.json", "r", encoding='utf-8') as file:
        data = json.load(file)
    auth_token = data.get("authToken")

    if await is_token_valid(auth_token):
        return auth_token

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Открываем страницу логина
        URL = "https://eos.bgitu.ru/Account/Login.aspx"
        await page.goto(URL)

        # Вводим логин
        await page.fill("#ctl00_MainContent_ucLoginFormPage_tbUserName_I", login)

        # Вводим пароль
        await page.fill(
            "#ctl00_MainContent_ucLoginFormPage_tbPassword_I_CLND", password
        )
        await page.press(
            "#ctl00_MainContent_ucLoginFormPage_tbPassword_I_CLND", "Enter"
        )  # Нажимаем Enter

        # Ждем редиректа и загрузки новой страницы
        await page.wait_for_timeout(4000)

        # Достаем authToken из куков
        cookies = await page.context.cookies()
        auth_token = next(
            (cookie["value"] for cookie in cookies if cookie["name"] == "authToken"),
            None,
        )

        # Закрываем браузер
        await browser.close()

        with open("data/auth_token.json", "w", encoding='utf-8') as file:
            json.dump({"authToken": auth_token}, file)

        return auth_token


async def is_token_valid(auth_token: str) -> bool:
    header_base64, payload_base64, _ = auth_token.split(".")
    payload_json = base64.urlsafe_b64decode(
        payload_base64 + "=" * (-len(payload_base64) % 4)
    )
    payload = json.loads(payload_json)
    exp_timestamp = payload.get("exp")

    # 1‑я проверка
    exp_time = datetime.fromtimestamp(exp_timestamp)
    current_time = datetime.now()
    if exp_time - current_time <= timedelta(days=1):
        return False

    # 2-я проверка
    async with aiohttp.ClientSession() as http_session:
        req = await http_session.get(
            url=f"https://eos.bgitu.ru/api/UserInfo/Student?studentID=-6169",  # Просто ссылка
            cookies={"authToken": auth_token},
        )
        return True if req.status == 200 else False


async def test_playwright():

    login = settings.SERVICE_ACCOUNT_LOGIN
    password = settings.SERVICE_ACCOUNT_PASSWORD

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Открываем страницу логина
        URL = "https://eos.bgitu.ru/Account/Login.aspx"
        await page.goto(URL)

        # Вводим логин
        await page.fill("#ctl00_MainContent_ucLoginFormPage_tbUserName_I", login)

        # Вводим пароль
        await page.fill(
            "#ctl00_MainContent_ucLoginFormPage_tbPassword_I_CLND", password
        )
        await page.press(
            "#ctl00_MainContent_ucLoginFormPage_tbPassword_I_CLND", "Enter"
        )  # Нажимаем Enter

        # Ждем редиректа и загрузки новой страницы
        await page.wait_for_timeout(4000)

        # Достаем authToken из куков
        cookies = await page.context.cookies()
        auth_token = next(
            (cookie["value"] for cookie in cookies if cookie["name"] == "authToken"),
            None,
        )

        # Закрываем браузер
        await browser.close()

