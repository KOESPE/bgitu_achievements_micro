import json
from typing import List, Optional

import jmespath
import aiohttp

from fastapi import APIRouter, Query

from modules.service_account import get_service_access_token

ratings_router = APIRouter()


def merge_json(data1, data2, using_types=False):
    combined_data = {}
    keys = ["listWorks", "categories", "faculs", "groups"]
    if using_types:
        keys.append("types")
    for key in keys:
        list1_str = [json.dumps(item) for item in data1.get(key, [])]
        list2_str = [json.dumps(item) for item in data2.get(key, [])]
        combined_list = [json.loads(item) for item in set(list1_str + list2_str)]
        combined_data[key] = combined_list
    return combined_data



def aggregate_ratings(data, filters=None):
    students = {}
    group_map = {g["id"]: g["name"] for g in data["groups"]}
    category_map = {c["categoryID"]: c["description"] for c in data["categories"]}
    type_map = {
        t["typeID"]: {"name": t["name"], "value": t["ballStudents"]}
        for t in data["types"]
    }

    achievement_category_filter = filters.get("achievementCategory")
    achievement_category_values = (
        {item["value"] for item in achievement_category_filter}
        if achievement_category_filter
        else None
    )

    faculty_filter = filters.get("faculty")
    faculty_value = faculty_filter[0]["value"] if faculty_filter else None

    query = jmespath.compile(
        "listWorks[*].{studentID: studentID, fullName: fullName, groupID: groupID, categoryID: categoryID, ballOfWork: ballOfWork, faculID: faculID, typeID: typeID, status: status}"
    )
    works = query.search(data)

    for work in works:
        if work["ballOfWork"] <= 0:
            continue

        if faculty_value and work["faculID"] != faculty_value:
            continue

        if (
            achievement_category_values
            and work["categoryID"] not in achievement_category_values
        ):
            continue

        student_id = work["studentID"]
        if student_id not in students:
            students[student_id] = {
                "fullName": work["fullName"],
                "studentId": student_id,
                "groupName": group_map.get(work["groupID"], "Неизвестно"),
                "verifiedScore": 0,
                "verifiedData": {},
                "unVerifiedScore": 0,
                "unVerifiedData": {},
            }

        if work["status"] == 13:  # Verified
            category_name = category_map.get(work["categoryID"], "Прочее")
            type_info = type_map.get(work["typeID"], {"name": "name", "value": 0})

            if category_name not in students[student_id]["verifiedData"]:
                students[student_id]["verifiedData"][category_name] = {
                    "value": 0,
                    "types": [],
                }

            students[student_id]["verifiedData"][category_name]["value"] += work[
                "ballOfWork"
            ]
            students[student_id]["verifiedData"][category_name]["types"].append(
                type_info
            )
            students[student_id]["verifiedScore"] += work["ballOfWork"]
        elif work["status"] == 1:  # Unverified
            category_name = category_map.get(work["categoryID"], "Прочее")
            type_info = type_map.get(work["typeID"], {"name": "name", "value": 0})

            if category_name not in students[student_id]["unVerifiedData"]:
                students[student_id]["unVerifiedData"][category_name] = {
                    "value": 0,
                    "types": [],
                }

            students[student_id]["unVerifiedData"][category_name]["value"] += work[
                "ballOfWork"
            ]
            students[student_id]["unVerifiedData"][category_name]["types"].append(
                type_info
            )
            students[student_id]["unVerifiedScore"] += work["ballOfWork"]

    for student in students.values():
        # verifiedData
        for category_name, data in student["verifiedData"].items():
            # Агрегируем типы внутри каждой категории
            aggregated_types = {}
            for type_info in data["types"]:
                type_name = type_info["name"]
                type_value = (
                    type_info.get("value") or 0
                )  # Если value нет или None, то считаем его 0
                if type_name not in aggregated_types:
                    aggregated_types[type_name] = {"name": type_name, "value": 0}
                aggregated_types[type_name]["value"] += type_value

            # Преобразуем обратно в список
            student["verifiedData"][category_name]["types"] = list(
                aggregated_types.values()
            )

        # unVerifiedData
        for category_name, data in student["unVerifiedData"].items():
            # Агрегируем типы внутри каждой категории
            aggregated_types = {}
            for type_info in data["types"]:
                type_name = type_info["name"]
                type_value = (
                    type_info.get("value") or 0
                )  # Если value нет или None, то считаем его 0
                if type_name not in aggregated_types:
                    aggregated_types[type_name] = {"name": type_name, "value": 0}
                aggregated_types[type_name]["value"] += type_value

            # Преобразуем обратно в список
            student["unVerifiedData"][category_name]["types"] = list(
                aggregated_types.values()
            )

    result = []
    for student in students.values():
        verified_data = [
            {"categoryName": cat, "value": data["value"], "types": data["types"]}
            for cat, data in student["verifiedData"].items()
        ]
        unverified_data = [
            {"categoryName": cat, "value": data["value"], "types": data["types"]}
            for cat, data in student["unVerifiedData"].items()
        ]
        result.append(
            {
                **student,
                "verifiedData": verified_data,
                "unVerifiedData": unverified_data,
            }
        )

    return result


@ratings_router.get("/ratings/filters")
async def get_filters():
    with open("data/filters.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


@ratings_router.get("/ratings/")
async def get_ratings(
    achievementCategory: Optional[List[int]] = Query(default=None),
    faculty: Optional[int] = Query(default=None),
):
    async with aiohttp.ClientSession() as http_session:
        auth_token = await get_service_access_token()
        raw_data = None
        for is_verified_works in ["true", "false"]:
            years = ["2022-2023", "2023-2024", "2024-2025", "2025-2026"]
            for year in years:
                req = await http_session.get(
                    url=f"https://eos.bgitu.ru/api/Portfolio/Verifier/ListWorks?year={year}&sem=-1&finished={is_verified_works}&type=0&sql=true",
                    cookies={"authToken": auth_token},
                )
                data = await req.json()

                if raw_data is None:
                    raw_data = data["data"]
                else:
                    raw_data = merge_json(raw_data, data["data"], using_types=True)

    filters = {}
    if achievementCategory:
        filters["achievementCategory"] = [{"value": cat} for cat in achievementCategory]
    if faculty:
        filters["faculty"] = [{"value": faculty}]
    ratings = aggregate_ratings(raw_data, filters=filters)
    return ratings


@ratings_router.get("/getDiagramData")
async def get_ratings(studentId: int):
    typeid_data = [
        {"typeID": [1, 44, 2], "name": "Публикации и учебные материалы"},
        {"typeID": [43, 61, 62, 65, 66, 67, 68, 73], "name": "Научная деятельность"},
        {"typeID": [64, 76, 63, 60, 77], "name": "Признание и развитие"},
        {"typeID": [47, 49, 78, 80, 81], "name": "НИР и Инновации"},
        {"typeID": [8, 72, 74, 75], "name": "Гранты и НИРС"},
        {"typeID": [39, 50, 6, 42, 7], "name": "РИД и интеллектуальная собственность"},
        {"typeID": [9], "name": "Научные стажировки"},
        {"typeID": [3, 52, 70], "name": "Конкурсы"},
        {"typeID": [4, 5], "name": "Выставки и Конференции"},
        {"typeID": [11, 15, 33, 32, 34, 35], "name": "Спорт и соревнования"},
        {"typeID": [16, 17], "name": "Творчество"},
        {
            "typeID": [18, 19, 20, 21, 22, 23, 24, 25, 26],
            "name": "Общественная деятельность",
        },
    ]

    async with aiohttp.ClientSession() as http_session:
        auth_token = await get_service_access_token()
        req = await http_session.get(
            url=f"https://eos.bgitu.ru/api/Portfolio/ListWorks?userID=-{studentId}&allWorks=true",
            cookies={"authToken": auth_token},
        )
        data = await req.json()
    all_works = data["data"]["listWorks"]

    # Все данные
    category_work_all = {}
    category_work_verified = {}

    for category in typeid_data:
        category_work_all[category["name"]] = sum(
            work["ballOfWork"]
            for work in all_works
            if work["typeID"] in category["typeID"] and work["ballOfWork"] > 0
        )
        category_work_verified[category["name"]] = sum(
            work["ballOfWork"]
            for work in all_works
            if work["typeID"] in category["typeID"]
            and work["ballOfWork"] > 0
            and work["status"] == 13
        )

    all_data_list = [
        {"name": name, "value": value} for name, value in category_work_all.items()
    ]
    verified_data_list = [
        {"name": name, "value": value} for name, value in category_work_verified.items()
    ]

    return {"allData": all_data_list, "VerifiedData": verified_data_list}
