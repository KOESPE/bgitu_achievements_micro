import aiohttp

from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

users_router = APIRouter(tags=["Пользователи"])


class authPayload(BaseModel):
    login: str
    password: str


@users_router.post("/auth")
async def get_role(response: Response, credentials: authPayload):
    """
    {"role": "student"} {"role": "non-student"}
    """
    login = credentials.login
    password = credentials.password.strip()

    # Для тестирования
    if login == "admin" and password == "admin":
        return {"role": "non-student"}

    async with aiohttp.ClientSession() as http_session:
        auth_req = await http_session.post(
            url="https://eos.bgitu.ru/api/tokenauth",
            json={"userName": login, "password": password},
        )
        auth_resp = await auth_req.json()

        if auth_resp.get("state") == -1:
            raise HTTPException(detail="Неправильный логин или пароль", status_code=401)

        user_roles = auth_resp["data"]["user"]["roles"]
        for role in user_roles:
            if role["name"] == "Студент":
                return {"role": "student"}

        return {"role": "non-student"}
