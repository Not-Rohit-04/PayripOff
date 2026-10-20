from fastapi import FastAPI 

app = FastAPI()

@app.get("/helloo")
def get_helloo():
    return {"message": "Hello, World!"}