from datetime import datetime, timedelta
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import User, UserRole

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    name: Optional[str] = None
    corporate_code: Optional[str] = None
    operator_number: Optional[int] = None

class UserCreate(BaseModel):
    email: str
    password: str
    role: UserRole
    name: Optional[str] = None
    phone: Optional[str] = None
    corporate_code: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Prepare operator number if role is operator
    corp_code = (user_in.corporate_code or "").strip()
    op_number: Optional[int] = None
    if user_in.role == UserRole.operator:
        # extract last 6 digits if present, else generate unique
        import random, re
        digits = "".join(re.findall(r"\d", corp_code))[-6:]
        if digits and digits.isdigit():
            op_number = int(digits)
            # ensure unique; if exists, regenerate random
            if db.query(User).filter(User.operator_number == op_number).first():
                op_number = None
        if op_number is None:
            while True:
                candidate = random.randint(100000, 999999)
                if not db.query(User).filter(User.operator_number == candidate).first():
                    op_number = candidate
                    break
        if corp_code:
            # if provided code is already used, treat as registration error -> FE will redirect to login
            if db.query(User).filter(User.corporate_code == corp_code).first():
                raise HTTPException(status_code=400, detail="Corporate code already registered")
        else:
            corp_code = f"VTB{op_number:06d}"
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        name=user_in.name,
        phone=user_in.phone,
        corporate_code=corp_code or None,
        operator_number=op_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, email=user.email, role=user.role, name=user.name, corporate_code=user.corporate_code, operator_number=user.operator_number)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)