import json
import secrets
import time
import uuid
from collections.abc import Iterator

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from building_with_rag.config import Settings, get_settings
from building_with_rag.models import QueryRequest, QueryResult
from building_with_rag.openai_models import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionDelta,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelCard,
    ModelList,
    OpenAIErrorBody,
    OpenAIErrorEnvelope,
)
from building_with_rag.registry import MODE_REGISTRY, MODEL_TO_MODE, run_pattern


class OpenAIError(Exception):
    def __init__(self, status_code: int, message: str, type_: str, code: str | None = None):
        self.status_code = status_code
        self.message = message
        self.type = type_
        self.code = code


def _envelope(status_code: int, message: str, type_: str, code: str | None = None) -> JSONResponse:
    body = OpenAIErrorEnvelope(error=OpenAIErrorBody(message=message, type=type_, code=code))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def require_api_key(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.capstone_api_key
    if not expected:
        return
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise OpenAIError(
            401, "Invalid or missing API key.", "invalid_request_error", "invalid_api_key"
        )


app = FastAPI(title="Building with RAG")


@app.exception_handler(OpenAIError)
async def openai_error_handler(_: Request, exc: OpenAIError) -> JSONResponse:
    return _envelope(exc.status_code, exc.message, exc.type, exc.code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if request.url.path.startswith("/v1/chat/"):
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", ()))
        return _envelope(
            400, f"Invalid request: {loc}: {first.get('msg', 'invalid')}", "invalid_request_error"
        )
    # Report location and message only; never echo submitted input values.
    detail = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in errors]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/healthz")
def healthz(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "app_env": settings.app_env}


@app.post("/v1/query", response_model=QueryResult, dependencies=[Depends(require_api_key)])
def query(request: QueryRequest) -> QueryResult:
    return run_pattern(request)


@app.get("/v1/models", response_model=ModelList, dependencies=[Depends(require_api_key)])
def list_models() -> ModelList:
    return ModelList(data=[ModelCard(id=model_id) for model_id in MODE_REGISTRY.values()])


def _stream(completion_id: str, created: int, model: str, text: str) -> Iterator[str]:
    def frame(delta: ChatCompletionDelta, finish: str | None = None) -> str:
        chunk = ChatCompletionChunk(
            id=completion_id,
            created=created,
            model=model,
            choices=[ChatCompletionChunkChoice(delta=delta, finish_reason=finish)],
        )
        data = chunk.model_dump()
        data["choices"][0]["delta"] = delta.model_dump(exclude_none=True)
        return f"data: {json.dumps(data)}\n\n"

    yield frame(ChatCompletionDelta(role="assistant"))
    yield frame(ChatCompletionDelta(content=text))
    yield frame(ChatCompletionDelta(), "stop")
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)], response_model=None)
def chat_completions(
    body: ChatCompletionRequest, settings: Settings = Depends(get_settings)
) -> StreamingResponse | ChatCompletionResponse:
    mode = MODEL_TO_MODE.get(body.model)
    if mode is None:
        raise OpenAIError(
            404,
            f"The model '{body.model}' does not exist.",
            "invalid_request_error",
            "model_not_found",
        )
    question = next((m.content for m in reversed(body.messages) if m.role == "user"), None)
    if not question or not question.strip():
        raise OpenAIError(400, "A non-empty user message is required.", "invalid_request_error")

    fields: dict = {}
    options = body.rag_options
    if options:
        if options.pattern:
            mode = options.pattern
        if options.filters:
            fields["filters"] = options.filters
        if options.limit is not None:
            fields["limit"] = options.limit
        if options.required_acts is not None:
            fields["required_acts"] = options.required_acts
        if options.chapter is not None:
            fields["chapter"] = options.chapter
    try:
        # caller_id and generate_answer are set by the server; browser values are ignored.
        query_request = QueryRequest(
            question=question,
            pattern=mode,
            caller_id=settings.webui_demo_caller_id,
            generate_answer=False,
            **fields,
        )
    except ValidationError as exc:
        raise OpenAIError(400, "Invalid message or rag_options.", "invalid_request_error") from exc

    result = run_pattern(query_request)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    if body.stream:
        return StreamingResponse(
            _stream(completion_id, created, body.model, result.message),
            media_type="text/event-stream",
        )
    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=body.model,
        choices=[ChatCompletionChoice(message=ChatCompletionMessage(content=result.message))],
    )
