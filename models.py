from pydantic import BaseModel, Field
from typing import Optional


class UserRegister(BaseModel):

    username: str
    email: str
    password: str


class UserLogin(BaseModel):

    username: str
    password: str


class Token(BaseModel):

    token: str
    token_type: str


class AlbumOut(BaseModel):

    album_id: str
    album_name: str
    artist_name: str
    artist_id: str
    release_date: str
    cover: str


class ReviewCreate(BaseModel):

    user_id: int
    rating: int = Field(ge=0, lt=5)
    review: Optional[str] = ""


class ReviewDelete(BaseModel):

    user_id: int
    # we don t need album_id here because it comes through the request


class ReviewOut(BaseModel):
    album_name: str
    artist_name: str
    cover: str
    rating: int
    review: Optional[str]


class FavoriteCreate(BaseModel):

    user_id: int


class FollowerCreate(BaseModel):

    user_id: int


class FavoritesOut(BaseModel):

    album_id: str


class FollowDelete(BaseModel):

    user_id: int


class FollowersOut(BaseModel):

    id: int
    username: str


class FollowingOut(BaseModel):

    id: int
    username: str


class UserProfileOut(BaseModel):

    id: int
    username: str
    bio: str
    picture: str
    favorites: list[FavoritesOut]
    followers_count: int
    following_count: int
    reviews: list[ReviewOut]


class ActivityOut(BaseModel):

    album_name: str
    artist_name: str
    cover: str
    rating: int
    review: Optional[str] = ""


class BioUpdate(BaseModel):

    bio: str


class PictureUpdate(BaseModel):

    picture: str
