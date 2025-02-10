import io

import aiohttp
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from modules.service_account import get_service_access_token


# Исходные данные
async def get_ratings_data(studentId: int):
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


def create_radar_chart(data):
    df_all = pd.DataFrame(data["allData"])
    df_verified = pd.DataFrame(data["VerifiedData"])

    categories = df_all["name"].tolist()
    values_all = df_all["value"].tolist()
    values_verified = df_verified["value"].tolist()

    label_loc = np.linspace(
        start=0, stop=2 * np.pi, num=len(values_all), endpoint=False
    )

    plt.figure(figsize=(10, 10))
    ax = plt.subplot(111, polar=True)

    values_all += values_all[:1]
    values_verified += values_verified[:1]
    label_loc = np.append(label_loc, label_loc[0])

    plt.plot(
        label_loc,
        values_all,
        marker="o",
        linestyle="-",
        color="b",
        label="Все достижения",
    )
    plt.fill(label_loc, values_all, alpha=0.25, color="b")

    plt.plot(
        label_loc,
        values_verified,
        marker="o",
        linestyle="-",
        color="r",
        label="Проверенные достижения",
    )
    plt.fill(label_loc, values_verified, alpha=0.25, color="r")

    plt.xticks(label_loc[:-1], labels=categories, size=12, color="black")
    plt.yticks(
        np.arange(0, max(max(values_all), max(values_verified)) + 10, 10),
        color="grey",
    )
    plt.ylim(
        0, max(max(values_all), max(values_verified)) + 10
    )  # Установка лимитов для оси Y

    plt.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return buf
