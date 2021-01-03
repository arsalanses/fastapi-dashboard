from starlette.responses import Response, HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyCookie
from database import SessionLocal, engine
from models import Base, User, Item
from sqlalchemy.orm import Session
from pydantic import BaseModel
from starlette import status
from jose import jwt

app = FastAPI()

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

cookie_sec = APIKeyCookie(name="session")

secret_key = "r49dkKYBlNNLzMd2SiWclNCMTnhoZuUaLMilW9HYgaE="

class AddItemRequest(BaseModel):
    Name: str
    Value: int
    Score: float

class RemoveItemRequest(BaseModel):
    Name: str

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(session: str = Depends(cookie_sec), db: Session = Depends(get_db)):

    # users = db.query(User)
    
    try:
        payload = jwt.decode(session, secret_key)
        user = db.query(User).filter(User.email==payload["sub"]).first()
    
        return user
    
    except Exception:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication")

@app.get("/")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):

    users = db.query(User).filter(User.email==username).first()
    
    if not users:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user or password")
    
    db_password = users.hashed_password
    if not password == db_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user or password")

    token = jwt.encode({"sub": username}, secret_key)
    rr = RedirectResponse('/private', status_code=303)
    rr.set_cookie(key="session", value=token)

    return rr

@app.get("/private")
def read_private(request: Request, name = None, username: str = Depends(get_current_user), db: Session = Depends(get_db)):

    item = db.query(Item).filter(Item.owner_id==username.id)

    if name:
        item = item.filter(Item.Name.like(name))

    sum_value = 0
    sum_score = 0
    for course in item:
        sum_score += course.Score * course.Value
        sum_value += course.Value
    sum_value = sum_value if sum_value != 0 else 1

    return templates.TemplateResponse("home.html",
    {
    "request": request,
    "courses": item,
    "email": username.email,
    "owner_id": username.id,
    "total": sum_score / sum_value
    })

@app.post("/add")
def create_item(item_request: AddItemRequest, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    item = Item()
    item.Name = item_request.Name
    item.Score = item_request.Score
    item.Value = item_request.Value
    item.owner_id = username.id

    db.add(item)
    db.commit()

    return {
        "code": "success",
        "message": "item added"
    }

@app.delete("/remove")
def remove_course(item_request: RemoveItemRequest, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Item).filter(Item.owner_id==username.id, Item.Name==item_request.Name).delete()
    db.commit()

    return {
        "code": "success",
        "message": "course removed"
    }

@app.get("/logout")
def logout(response: Response):
    response.set_cookie("session", 0)    
    return {"ok": True}
