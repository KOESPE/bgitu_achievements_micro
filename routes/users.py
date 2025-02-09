import datetime
from typing import Union

from icecream import ic
import aiohttp

from fastapi import APIRouter, Depends, Request, Response, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel

users_router = APIRouter(tags=["Пользователи"])

security = HTTPBearer()


class authPayload(BaseModel):
    login: str
    password: str


@users_router.post("/auth")
async def get_role(response: Response, credentials: authPayload):
    """
    Пока что возвращает только non-student -> показываем весь интерфейс
    """
    login = credentials.login
    password = credentials.password.strip()

    async with aiohttp.ClientSession() as http_session:
        auth_req = await http_session.post(
            url="https://eos.bgitu.ru/api/tokenauth",
            json={"userName": login, "password": password},
        )
        auth_resp = await auth_req.json()

        if auth_resp.get("state") == -1:
            raise HTTPException(detail="Неправильный логин или пароль", status_code=401)

        access_token_eos = auth_resp["data"]["accessToken"]
        student_id = abs(int(auth_resp["data"]["data"]["id"]))

        user_data_req = await http_session.get(
            url=f"https://eos.bgitu.ru/api/UserInfo/Student?studentID={student_id}",
            cookies={"authToken": access_token_eos},
        )

        student_data = await user_data_req.json()
        student_data = student_data["data"]

        fullname = f"{student_data['surname']} {student_data['name']} {student_data['middleName']}".strip()
        group_name = student_data["group"]["item1"].upper()
        admission_year = int(student_data["admissionYear"])
        course_number = int(student_data["course"])
        department = student_data["kaf"]["kafName"]
        faculty = student_data["facul"]["faculName"]
        gradebook = student_data["numRecordBook"]
        email = student_data["email"]
        phone_number = student_data["numberMobile"]

    return {"role": "non-student"}
