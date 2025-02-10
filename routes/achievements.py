import asyncio
import time

import jmespath
from icecream import ic
import aiohttp

from fastapi import APIRouter


from modules.service_account import get_service_access_token

achievements_router = APIRouter(prefix="/achievements")


@achievements_router.get("/worksForVerifications")
async def worksForVerifications():
    time_start = time.time()
    async with aiohttp.ClientSession() as http_session:
        auth_token = await get_service_access_token()
        parsed_works = []

        years = ["2022-2023", "2023-2024", "2024-2025", "2025-2026"]
        for year in years:
            req = await http_session.get(
                url=f"https://eos.bgitu.ru/api/Portfolio/Verifier/ListWorks?year={year}&sem=-1&finished=false&type=0&sql=true",
                cookies={"authToken": auth_token},
            )
            data = await req.json()

            query = "data.listWorks[?ballOfWork > `0`].{fullName: fullName, groupID: groupID, category: category, link: join('', ['https://eos.bgitu.ru/WebApp/#/portfolio/work/', to_string(typeID), '/', to_string(workID)])}"
            works = jmespath.search(query, data)

            group_query = "data.groups[*].{id: id, name: name}"
            groups = {g["id"]: g["name"] for g in jmespath.search(group_query, data)}

            for work in works:
                work["groupName"] = groups.get(work.pop("groupID"), "Неизвестная группа")
            parsed_works.extend(works)
        ic(parsed_works)
        ic(time.time() - time_start)
        return parsed_works

