import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio

app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://newspaper:newspaper2021@cluster0.wc9gy.mongodb.net/news?retryWrites=true&w=majority")
db = client.news

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class NewsModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(...)
    description: str = Field(...)
    author: str = Field(...)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "title": "Buraco de minhoca descoberto",
                "description": "Buraco de minhoca é encontrado na orbita de jupiter",
                "author": "NY Times"
            }
        }


class UpdateNewsModel(BaseModel):
    title: Optional[str]
    description: Optional[str]
    author: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "title": "Buraco de minhoca descoberto",
                "description": "Buraco de minhoca é encontrado na orbita de jupiter",
                "author": "NY Times"
            }
        }


@app.post("/", response_description="Add news", response_model=NewsModel)
async def create_news(news: NewsModel = Body(...)):
    news = jsonable_encoder(news)
    new_news = await db["news"].insert_one(news)
    created_news = await db["news"].find_one({"_id": new_news.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_news)


@app.get(
    "/", response_description="List all news", response_model=List[NewsModel]
)
async def list_news():
    news = await db["news"].find().to_list(1000)
    return news


@app.get(
    "/{q}", response_description="Search for a news", response_model=List[NewsModel]
)
async def search_news(q: str):
    news = await db["news"].find({"*": q}).to_list(1000)
    return news

@app.put("/{id}", response_description="Update a news", response_model=NewsModel)
async def update_news(id: str, news: UpdateNewsModel = Body(...)):
    news = {k: v for k, v in news.dict().items() if v is not None}

    if len(news) >= 1:
        update_result = await db["news"].update_one({"_id": id}, {"$set": news})

        if update_result.modified_count == 1:
            if (
                updated_news := await db["news"].find_one({"_id": id})
            ) is not None:
                return updated_news

    if (existing_news := await db["news"].find_one({"_id": id})) is not None:
        return existing_news

    raise HTTPException(status_code=404, detail=f"news {id} not found")


@app.delete("/{id}", response_description="Delete a news")
async def delete_news(id: str):
    delete_result = await db["news"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"news {id} not found")
