from user_manager import UserManager
from review_manager import ReviewManager
import os
from spotify import get_spotify_token, search_for_artist_albums, search_for_album
from datetime import datetime, timedelta
from dotenv import load_dotenv
from init_db import database
from fastapi import FastAPI, status, Response, HTTPException, Depends
from models import (
    AlbumOut,
    ReviewCreate,
    ReviewDelete,
    ReviewOut,
    FavoriteCreate,
    FollowerCreate,
    FavoritesOut,
    FollowDelete,
    FollowersOut,
    FollowingOut,
    UserProfileOut,
    ActivityOut,
    BioUpdate,
    PictureUpdate,
    UserRegister,
    UserLogin,
    User,
)
from auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
review_manager = ReviewManager()
user_manager = UserManager()

# CORS setup to allow frontend access during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/")
def home():
    return "musicboxd_backend is up and running"


# USER FUNCTIONS


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):

    existing = await database.fetch_one(
        "select * from users where username = :username", {"username": user.username}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    hashed_password = hash_password(user.password)
    await database.execute(
        "insert into users (username, password_hash) values (:username, :password_hash)",
        {"username": user.username, "password_hash": hashed_password},
    )

    return {"message": "User successfully registered"}


@app.post("/login", status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):

    user = await database.fetch_one(
        "select id, username, password_hash from users where username = :username",
        {"username": form_data.username},
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Username not found"
        )
    hashed_password = user["password_hash"]

    if not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password"
        )

    # after the user credentials are verified, we have to return a jwt token

    token = create_access_token({"sub": str(user["id"])})

    return {"access_token": token, "token_type": "bearer"}


# REVIEWS FUNCTIONS


@app.get(
    "/search/artist/{artist_name}",
    response_model=list[AlbumOut],
    status_code=status.HTTP_200_OK,
)
async def search_artists_albums(
    artist_name: str, user: User = Depends(get_current_user)
):  # we don t need current user data here, but by adding the dependency the request will wait for the JWT Token, so only logged in user can use this

    token = await get_spotify_token()
    albums_list: list[AlbumOut] = []
    albums = await search_for_artist_albums(token, artist_name)
    for album in albums:
        album_data = AlbumOut(
            album_id=album["id"],
            album_name=album["name"],
            artist_name=album["artists"][0]["name"],
            artist_id=album["artists"][0]["id"],
            release_date=album["release_date"],
            cover=album["images"][0]["url"],
        )
        await database.execute(
            """
            INSERT INTO albums
            (album_id, album_name, artist_name, artist_id, release_date, cover)
            VALUES (:album_id, :album_name, :artist_name, :artist_id, :release_date, :cover)
            ON CONFLICT (album_id) DO NOTHING
            """,
            album_data.model_dump(),  # converts the AlbumOut object (called album_data) from a Pydantic model
            # to a python dictionary; :album_id, :album_name etc. are placeholder names for variables
            # that will be replaced by album_id, album_name etc. from the python dictionary
        )
        albums_list.append(album_data)

    return albums_list


@app.get(
    "/search/album/{album_name}",
    response_model=list[AlbumOut],
    status_code=status.HTTP_200_OK,
)
async def search_album(album_name: str, user: User = Depends(get_current_user)):

    pattern = f"%{album_name}%"
    existing = await database.fetch_one(
        "SELECT * FROM albums WHERE lower(album_name) ILIKE lower(:pattern)",
        {
            "pattern": pattern
        },  # as before, :album_name is a placeholder, which will be replaced by the album_name variable passed to the function
    )

    if not existing:

        token = await get_spotify_token()
        album = await search_for_album(token, album_name)  # returns a dictionary

        album_data = AlbumOut(
            album_id=album["id"],
            album_name=album["name"],
            artist_name=album["artists"][0]["name"],
            artist_id=album["artists"][0]["id"],
            release_date=album["release_date"],
            cover=album["images"][0]["url"],
        )

        await database.execute(
            """
                           INSERT INTO albums (album_id, album_name, artist_name, artist_id, release_date, cover) VALUES 
                (:album_id, :album_name, :artist_name, :artist_id, :release_date, :cover)
                ON CONFLICT (album_id) DO NOTHING""",
            album_data.model_dump(),
        )

    albums = await database.fetch_all(
        "SELECT * FROM albums WHERE lower(album_name) ILIKE lower(:pattern)",
        {"pattern": pattern},
    )
    result: list[AlbumOut] = []
    result = [
        AlbumOut(
            album_id=row["album_id"],
            album_name=row["album_name"],
            artist_name=row["artist_name"],
            artist_id=row["artist_id"],
            release_date=row["release_date"],
            cover=row["cover"],
        )
        for row in albums
    ]

    return result


# FOR THE MOMENT, WHERE WE NEED USER_ID WE WILL GET IT FROM THE PYDANTIC MODEL
# LATER, WHEN WE HAVE AUTH, WE WILL DO IT WITH Depends(get_current_user)


@app.post("/album/{album_id}/rating", status_code=status.HTTP_200_OK)
async def rate_album(
    album_id: str, review: ReviewCreate, user: User = Depends(get_current_user)
):  # review is an object of the ReviewCreate Pydantic class

    user_id = user.id
    success, message = await review_manager.add_review(
        user_id, album_id, review.rating, review.review
    )
    # add_review has async calls, and this call should also be await

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}  # fastapi automatically serializes this to json


@app.delete("/album/{album_id}/delete_rating", status_code=status.HTTP_200_OK)
async def delete_rate(album_id: str, user: User = Depends(get_current_user)):

    user_id = user.id
    success, message = await review_manager.delete_review(user_id, album_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}


# FAVORITES FUNCTION


@app.post("/album/{album_id}/add_favorite", status_code=status.HTTP_201_CREATED)
async def add_to_favorites(album_id: str, user: User = Depends(get_current_user)):

    user_id = user.id
    success, message = await user_manager.add_favourite(user_id, album_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}


@app.get(
    "/user/{username}/get_favorites",
    response_model=list[AlbumOut],
    status_code=status.HTTP_200_OK,
)
async def get_user_favorites(username: str, user: User = Depends(get_current_user)):

    searched_user = await database.fetch_one(
        "select id from users where username = :username", {"username": username}
    )
    if not searched_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    favorites = await user_manager.get_favorites(searched_user["id"])

    return favorites


# FOLLOWERS FUNCTIONS


@app.get("/user/{username}/search", status_code=status.HTTP_200_OK, response_model=User)
async def search_user(username: str, user: User = Depends(get_current_user)):

    searched_user_id = await user_manager.search_user(username)
    if not searched_user_id:
        raise HTTPException(status_code=404, detail="User not found")
    return User(id=searched_user_id, username=username)


@app.post("/user/{followed_id}/follow", status_code=status.HTTP_200_OK)
async def follow(followed_id: int, user: User = Depends(get_current_user)):

    follower_id = user.id

    if not follower_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User has to be logged in"
        )

    success, message = await user_manager.follow_user(follower_id, followed_id)

    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}


@app.delete("/user/{followed_id}/unfollow", status_code=status.HTTP_200_OK)
async def unfollow(followed_id: int, user: User = Depends(get_current_user)):

    follower_id = user.id

    if not follower_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User has to be logged in"
        )

    success, message = await user_manager.unfollow_user(follower_id, followed_id)

    if not success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}


@app.get(
    "/user/get_followers",
    response_model=list[FollowersOut],
    status_code=status.HTTP_200_OK,
)
async def get_follower(user: User = Depends(get_current_user)):
    followers = await user_manager.get_followers(user.id)
    followers_return: list[FollowersOut] = []
    for follower in followers:
        followers_return.append(follower)
    return followers_return


@app.get(
    "/user/get_following",
    response_model=list[FollowingOut],
    status_code=status.HTTP_200_OK,
)
async def get_following(user: User = Depends(get_current_user)):
    followings = await user_manager.get_following(user.id)
    followings_return: list[FollowingOut] = []
    for following in followings:
        followings_return.append(following)
    return followings_return


# USER PROFILE
@app.get(
    "/user/{username}/profile",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
)
async def get_profile(username, user: User = Depends(get_current_user)):

    user = await database.fetch_one(
        "SELECT id, username, bio, picture FROM users WHERE LOWER(username) = :username",
        {"username": username.lower()},
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user_data = {
        "id": user["id"],
        "username": user["username"],
        "bio": user["bio"],
        "picture": user["picture"],
    }

    favorites = await database.fetch_all(
        """
            SELECT a.album_id as album_id, a.album_name as album_name, a.artist_id as artist_id, a.artist_name as artist_name, a.release_date as release_date, a.cover as cover
            FROM favorites f
            JOIN albums a ON f.album_id = a.album_id
            WHERE f.user_id = :user_id
        """,
        {"user_id": user_data["id"]},
    )
    user_data["favorites"] = [
        AlbumOut(**dict(fav))
        for fav in favorites  # we have favorites being a list[AlbumOut] in the Pydantic model for UserProfileOut
    ]
    # the sql query returnes a list of dictionaries with the same keys as the name of the fields of AlbumOut => favorites is that list of dicts
    # so we create a list of AlbumOut objects, by unpacking the dict key-value pairs with the **operator

    row = await database.fetch_one(
        "SELECT COUNT(*) as count FROM followers WHERE followed_id = :user_id",
        {"user_id": user_data["id"]},
    )
    user_data["followers_count"] = row["count"]

    row = await database.fetch_one(
        "SELECT COUNT(*) as count FROM followers WHERE follower_id = :user_id",
        {"user_id": user_data["id"]},
    )
    user_data["following_count"] = row["count"]

    reviews = await review_manager.get_user_reviews(user["id"])
    user_data["reviews"] = [
        ReviewOut(**dict(r)) for r in reviews
    ]  # same as with favorites

    return UserProfileOut(
        id=user_data["id"],
        username=username,
        bio=user_data["bio"],
        picture=user_data["picture"],
        favorites=user_data["favorites"],
        followers_count=user_data["followers_count"],
        following_count=user_data["following_count"],
        reviews=user_data["reviews"],
    )


@app.get("/user/profile", response_model=UserProfileOut, status_code=status.HTTP_200_OK)
async def get_own_profile(user: User = Depends(get_current_user)):

    user = await database.fetch_one(
        "SELECT id, username, bio, picture FROM users WHERE id = :id",
        {"id": user.id},
    )

    user_data = {
        "id": user["id"],
        "username": user["username"],
        "bio": user["bio"],
        "picture": user["picture"],
    }

    favorites = await database.fetch_all(
        """
            SELECT a.album_id as album_id, a.album_name as album_name, a.artist_id as artist_id, a.artist_name as artist_name, a.release_date as release_date, a.cover as cover
            FROM favorites f
            JOIN albums a ON f.album_id = a.album_id
            WHERE f.user_id = :user_id
        """,
        {"user_id": user_data["id"]},
    )
    user_data["favorites"] = [
        AlbumOut(**dict(fav))
        for fav in favorites  # we have favorites being a list[AlbumOut] in the Pydantic model for UserProfileOut
    ]
    # the sql query returnes a list of dictionaries with the same keys as the name of the fields of AlbumOut => favorites is that list of dicts
    # so we create a list of AlbumOut objects, by unpacking the dict key-value pairs with the **operator

    row = await database.fetch_one(
        "SELECT COUNT(*) as count FROM followers WHERE followed_id = :user_id",
        {"user_id": user_data["id"]},
    )
    user_data["followers_count"] = row["count"]

    row = await database.fetch_one(
        "SELECT COUNT(*) as count FROM followers WHERE follower_id = :user_id",
        {"user_id": user_data["id"]},
    )
    user_data["following_count"] = row["count"]

    reviews = await review_manager.get_user_reviews(user["id"])
    user_data["reviews"] = [
        ReviewOut(**dict(r)) for r in reviews
    ]  # same as with favorites

    return UserProfileOut(
        id=user_data["id"],
        username=user_data["username"],
        bio=user_data["bio"],
        picture=user_data["picture"],
        favorites=user_data["favorites"],
        followers_count=user_data["followers_count"],
        following_count=user_data["following_count"],
        reviews=user_data["reviews"],
    )


@app.get(
    "/user/friends_activity",
    response_model=list[ActivityOut],
    status_code=status.HTTP_200_OK,
)
async def friends_activity(user: User = Depends(get_current_user)):

    recent_activity = await review_manager.friends_recent_activity(user.id)
    return recent_activity


@app.put("/user/update_bio", status_code=status.HTTP_200_OK)
async def update_bio(bio: BioUpdate, user: User = Depends(get_current_user)):

    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not logged in"
        )

    bio_text = bio.bio

    await database.execute(
        "UPDATE users SET bio = :bio WHERE id = :id", {"bio": bio_text, "id": user.id}
    )

    return {"message": "Bio successfully updated"}


@app.put("/user/update_picture", status_code=status.HTTP_200_OK)
async def update_picture(
    picture: PictureUpdate, user: User = Depends(get_current_user)
):

    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not logged in"
        )

    picture_url = picture.picture

    await database.execute(
        "UPDATE users SET picture = :picture WHERE id = :id",
        {"picture": picture_url, "id": user.id},
    )

    return {"message": "Profile picture successfully updated"}


# RECOMANDATION ENGINE


@app.get("/user/get_recommendations", response_model=list[AlbumOut])
async def get_recommendations(user: User = Depends(get_current_user)):

    query = """
        SELECT
            a.album_id,
            a.album_name,
            a.artist_name,
            a.release_date,
            a.cover
        FROM recommendations r
        JOIN albums a ON a.album_id = r.album_id
        WHERE r.user_id = :user_id
        ORDER BY RANDOM()
        LIMIT 10
    """

    return await database.fetch_all(query, {"user_id": user.id})
