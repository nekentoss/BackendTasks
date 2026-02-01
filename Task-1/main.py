import asyncio
import time
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Data(BaseModel):
    numbers: List[int]
    delays: list[float]

class Result(BaseModel):
    number: int
    square: int
    delay: float
    time: float

class ResultFinal(BaseModel):
    results: List[Result]
    time_res: float
    parallel_faster_than_sequential: bool

#------
async def calculate_square(number: int, delay: float):

    start = time.perf_counter()

    await asyncio.sleep(delay)
    square = number * number

    end = time.perf_counter()

    return Result(
        number=number,
        square=square,
        delay=delay,
        time=round(end-start, 2)
    )

@app.post("/calculate/")
async def calculate(data: Data):
    start_res = time.perf_counter()
    tasks = []
    for number, delay in zip(data.numbers, data.delays):
        tasks.append(calculate_square(number, delay))
    
    results = await asyncio.gather(*tasks)
    end_res = time.perf_counter()
    time_res = round(end_res - start_res, 2)

    sequential_time = sum(data.delays)

    return ResultFinal(
        results=results,
        time_res=time_res,
        parallel_faster_than_sequential=time_res < sequential_time
    )