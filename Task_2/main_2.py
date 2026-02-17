from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
import json
import os
import re

app = FastAPI(title="Дз 2")


class Authorization(BaseModel):
    last_name: str
    first_name: str
    birth_date: date
    phone: str
    email: EmailStr

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value):
        if not re.fullmatch(r"[А-ЯЁ][а-яё]+", value):
            raise ValueError(
                "Фамилия должна быть с заглавной буквы и только кириллицей"
            )
        return value

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value):
        if not re.fullmatch(r"[А-ЯЁ][а-яё]+", value):
            raise ValueError(
                "Имя должно быть с заглавной буквы и только кириллицей"
            )
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if not re.fullmatch(r"\+?\d{10,15}", value):
            raise ValueError(
                "Телефон должен содержать 10–15 цифр, можно с +"
            )
        return value


@app.post("/subscriber")
def create_subscriber(request: Authorization):
    data = request.model_dump(mode="json")

    filename = f"data/{data['last_name']}_{data['first_name']}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return {
        "message": "Обращение успешно сохранено",
        "file": filename
    }