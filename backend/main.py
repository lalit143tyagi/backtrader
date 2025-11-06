from fastapi import FastAPI
from .database.connection import engine
from .database.models import Base

# This will create the tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Status": "Healthy"}
