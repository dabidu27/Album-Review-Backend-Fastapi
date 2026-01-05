from passlib.context import CryptContext
from dotenv import load_dotenv
import os
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from init_db import database
from models import User


load_dotenv()
ALGORITHM = os.getenv("ALGORITHM", "HS256")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
oauth2scheme = OAuth2PasswordBearer(tokenUrl="/login")


# oauth2scheme reads header requests, finds 'Authorization', extracts the token after Bearer and will pass it to get_current_user function
# Authorization: Bearer <JWT_TOKEN>
# tokenUrl = '/login' is only for swagger UI
def hash_password(password):

    return pwd_context.hash(password)


def verify_password(password, hashed_password):

    return pwd_context.verify(password, hashed_password)


def create_access_token(data, expires_minutes):

    # a JWT token is usually composed of 2 elements: sub - subject, who the token is about; our subject will be the user_id, passed thorugh data as a string
    # and exp - expire_date, when the token expire

    if "sub" not in data:
        raise ValueError("Token payload must include 'sub'")
    to_encode = data.copy()
    when_expires = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode["exp"] = when_expires  # we add an expiration timestamp to the token
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Depends = (oauth2scheme) means: before running the get_current_user function, run the oauth2scheme function on the request, to extract the jwt token
async def get_current_user(
    token: str = Depends(oauth2scheme),
) -> User:  # we return the Pydantic User model

    # to get the current user (their id), we have to decode the jwt token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub", None)
        if user_id is None:

            raise credentials_exception

    except JWTError:

        raise credentials_exception

    user = await database.fetch_one(
        "select id, username from users where id = :user_id",
        {"user_id": int(user_id)},
    )

    if user is None:
        raise credentials_exception

    return User(
        id=user["id"], username=user["username"]
    )  # we create the Pydantic class object using the dict given by the db query
