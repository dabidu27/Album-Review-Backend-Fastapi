from pydantic import BaseModel, Field
from typing import Optional


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


class FavoriteCreate(BaseModel):

    user_id: int


class FollowerCreate(BaseModel):

    user_id: int


class FavoritesOut(BaseModel):

    album_id: str
