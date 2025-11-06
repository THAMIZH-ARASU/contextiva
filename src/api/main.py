from fastapi import FastAPI


app = FastAPI(title="Contextiva API", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


