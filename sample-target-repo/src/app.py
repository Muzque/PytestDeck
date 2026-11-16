from typing import Any
from fastapi import FastAPI, Header, HTTPException, Request
from calculator import Calculator

app = FastAPI(title="Sample Target Service")
calc = Calculator()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "sample-target-repo"}

@app.post("/echo")
async def echo_payload(request: Request):
    try:
        body: Any = await request.json()
    except Exception:
        raw = await request.body()
        body = raw.decode("utf-8", errors="replace")
    return {
        "echo": body,
        "query": dict(request.query_params),
        "headers": dict(request.headers),
    }

@app.get("/large-payload")
def large_payload(lines: int = 200, keyword: str = "NEEDLE_TOKEN"):
    items = [
        {"index": i, "message": f"Record line {i} - {(keyword if i % 50 == 0 else 'standard_entry')}"}
        for i in range(1, max(1, min(lines, 5000)) + 1)
    ]
    return {"count": len(items), "items": items}

@app.get("/protected")
def protected_resource(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")
    return {"authenticated": True, "token": authorization.removeprefix("Bearer ").strip()}


@app.get("/calculate/add")
def add(a: float, b: float):
    return {"result": calc.add(a, b)}

@app.get("/calculate/divide")
def divide(a: float, b: float):
    try:
        return {"result": calc.divide(a, b)}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.get("/calculate/subtract")
def subtract(a: float, b: float):
    return {"result": calc.subtract(a, b)}

@app.get("/calculate/multiply")
def multiply(a: float, b: float):
    return {"result": calc.multiply(a, b)}

@app.get("/calculate/power")
def power(base: float, exp: float):
    return {"result": calc.power(base, exp)}

@app.get("/calculate/modulo")
def modulo(a: float, b: float):
    try:
        return {"result": calc.modulo(a, b)}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

