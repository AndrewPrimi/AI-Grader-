# grader_api.py
from fastapi import FastAPI
from pydantic import BaseModel
import openai

app = FastAPI()

class AnswerRequest(BaseModel):
    answer: str
    question: str

@app.post("/grade")
async def grade_answer(req: AnswerRequest):
    rubric = """
    Grade the student answer from 0 to 4:
    - 4: Excellent (complete & correct)
    - 3: Good (mostly correct, minor issue)
    - 2: Partial (some correct, missing key parts)
    - 1: Minimal (little correct)
    - 0: Incorrect
    Return JSON: {"score": X, "feedback": "..."}
    """

    prompt = f"""
    Question: {req.question}
    Student Answer: {req.answer}
    {rubric}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an AI grader."},
                  {"role": "user", "content": prompt}]
    )

    # Extract model reply
    return {"result": response.choices[0].message["content"]}