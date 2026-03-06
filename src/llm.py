from langchain_openai import ChatOpenAI

from src.config import (
    API_KEY,
    BASE_URL,
    MAIN_MODEL_ID,
    SUBAGENT_MODEL_ID,
)

main_model = ChatOpenAI(
    model=MAIN_MODEL_ID,
    temperature=0.0,
    api_key=API_KEY,
    base_url=BASE_URL,
)

report_model = ChatOpenAI(
    model=SUBAGENT_MODEL_ID["report"],
    temperature=0.0,
    api_key=API_KEY,
    base_url=BASE_URL,
)

research_model = ChatOpenAI(
    model=SUBAGENT_MODEL_ID["research"],
    temperature=0.0,
    api_key=API_KEY,
    base_url=BASE_URL,
)

scoping_model = ChatOpenAI(
    model=SUBAGENT_MODEL_ID["scoping"],
    temperature=0.0,
    api_key=API_KEY,
    base_url=BASE_URL,
)

verify_model = ChatOpenAI(
    model=SUBAGENT_MODEL_ID["verify"],
    temperature=0.0,
    api_key=API_KEY,
    base_url=BASE_URL,
)