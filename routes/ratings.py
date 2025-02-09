import asyncio
import datetime
import json
import os
import time
import uuid
from typing import Union, List, Optional, Mapping

import jmespath
from icecream import ic
import aiohttp

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    Header,
    HTTPException,
    Form,
    UploadFile,
    File,
    Query,
)


from modules.service_account import get_service_access_token

ratings_router = APIRouter(prefix="/ratings")


def merge_json(data1, data2, using_types=False):
    combined_data = {}
    keys = ["listWorks", "categories", "faculs", "groups"]
    if using_types:
        keys.append("types")
    for key in keys:
        # Преобразуем JSON-объекты в строки, чтобы использовать set для удаления дубликатов
        list1_str = [json.dumps(item) for item in data1.get(key, [])]
        list2_str = [json.dumps(item) for item in data2.get(key, [])]

        # Объединяем, удаляем дубликаты и преобразуем обратно в JSON-объекты
        combined_list = [json.loads(item) for item in set(list1_str + list2_str)]

        combined_data[key] = combined_list
    return combined_data


@ratings_router.get("/filters")
async def get_filters():
    with open("data/filters.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def aggregate_ratings(data, filters=None):
    students = {}
    group_map = {g["id"]: g["name"] for g in data["groups"]}
    category_map = {c["categoryID"]: c["description"] for c in data["categories"]}

    achievement_categories = {}
    achievement_category_filter = filters.get("achievementCategory")
    if achievement_category_filter is not None:
        achievement_categories = {
            item["value"]: item["name"] for item in achievement_category_filter
        }

    faculty_filter = {
        item["value"] for item in (filters.get("faculty") if filters else [])
    }

    query = jmespath.compile(
        "listWorks[*].{studentID: studentID, fullName: fullName, groupID: groupID, categoryID: categoryID, ballOfWork: ballOfWork, faculID: faculID}"
    )
    works = query.search(data)

    for work in works:
        if work["ballOfWork"] <= 0:
            continue

        if faculty_filter and work["faculID"] not in faculty_filter:
            continue

        student_id = work["studentID"]
        if student_id not in students:
            students[student_id] = {
                "fullName": work["fullName"],
                "studentId": student_id,
                "groupName": group_map.get(work["groupID"], "Неизвестно"),
                "verifiedScore": 0,
                "verifiedData": {},
            }

        category_name = category_map.get(work["categoryID"], "Прочее")
        if achievement_categories and work["categoryID"] not in achievement_categories:
            continue

        students[student_id]["verifiedData"].setdefault(category_name, 0)
        students[student_id]["verifiedData"][category_name] += work["ballOfWork"]
        students[student_id]["verifiedScore"] += work["ballOfWork"]

    result = []
    for student in students.values():
        student["verifiedData"] = [
            {"categoryName": cat, "value": score}
            for cat, score in student["verifiedData"].items()
        ]
        result.append(student)

    return result


@ratings_router.get("/")
async def get_ratings(
    achievementCategory: Optional[int] = Query(default=None),
    faculty: Optional[int] = Query(default=None),
):
    time_start = time.time()
    async with aiohttp.ClientSession() as http_session:
        auth_token = await get_service_access_token()
        raw_data = None

        years = ["2022-2023", "2023-2024", "2024-2025", "2025-2026"]
        for year in years:
            req = await http_session.get(
                url=f"https://eos.bgitu.ru/api/Portfolio/Verifier/ListWorks?year={year}&sem=-1&finished=true&type=0&sql=true",
                cookies={"authToken": auth_token},
            )
            data = await req.json()

            if raw_data is None:
                raw_data = data["data"]
            else:
                raw_data = merge_json(raw_data, data["data"])
    ic(raw_data)
    ic(time.time() - time_start)

    filters = {}
    if achievementCategory:
        filters["achievementCategory"] = [
            {"value": achievementCategory}
        ]  # Оборачиваем в список, как ты и ожидал
    if faculty:
        filters["faculty"] = [
            {"value": faculty}
        ]  # Оборачиваем в список, как ты и ожидал

    ratings = aggregate_ratings(
        raw_data, filters=filters
    )  # Передаем фильтры в aggregate_ratings
    ic(ratings)
    return ratings
