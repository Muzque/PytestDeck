from fastapi import FastAPI, HTTPException
from calculator import Calculator

app = FastAPI(title="Sample Target Service")
calc = Calculator()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "sample-target-repo"}

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

