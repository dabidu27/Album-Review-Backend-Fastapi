from user_manager import UserManager
from review_manager import ReviewManager
import os
from spotify import get_spotify_token, search_for_artist_albums, search_for_album
from datetime import datetime, timedelta
from dotenv import load_dotenv
from init_db import database
from fastapi import FastAPI, status, Response
from models import (
AlbumOut, ReviewCreate, ReviewDelete, FavoriteCreate, FollowerCreate, FavoritesOut, FollowDelete, 
FollowersOut, FollowingOut, UserProfileOut, ActivityOut, BioUpdate, PictureUpdate)


app = FastAPI()
review_manager = ReviewManager()
user_manager = UserManager()


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


@app.route("/register", methods=["POST"])
def register():


@app.route("/login", methods=["POST"])
def login():


@app.route("/logout", methods=["POST"])
def logout():


@app.route("/change_password", methods=["POST"])
def change_password():


# REVIEWS FUNCTIONS


@app.get(
    "/search/artist/{artist_name}",
    response_model=list[AlbumOut],
    status_code=status.HTTP_200_OK,
)
async def search_artists_albums(artist_name: str):

    token = get_spotify_token()
    albums_list: list[AlbumOut] = []
    albums = search_for_artist_albums(token, artist_name)
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
            album_data.model_dump(), #converts the AlbumOut object (called album_data) from a Pydantic model
            #to a python dictionary; :album_id, :album_name etc. are placeholder names for variables
            #that will be replaced by album_id, album_name etc. from the python dictionary
        )
        albums_list.append(album_data)

    return albums_list


@app.get(
    "/search/album/{album_name}",
    response_model=list[AlbumOut],
    status_code=status.HTTP_200_OK,
)
async def search_album(album_name: str):

    existing = await database.fetch_one(
        "SELECT * FROM albums WHERE album_name = :album_name",
        {'album_name': album_name} #as before, :album_name is a placeholder, which will be replaced by the album_name variable passed to the function
    )

    if not existing:

        token = get_spotify_token()
        album = search_for_album(token, album_name)  # returns a dictionary

        album_data = AlbumOut(
        album_id = album["id"],
        album_name = album["name"],
        artist_name = album["artists"][0]["name"],
        artist_id = album["artists"][0]["id"],
        release_date = album["release_date"],
        cover = album["images"][0]["url"])

        await database.execute(
            """
                           INSERT INTO albums (album_id, album_name, artist_name, artist_id, release_date, cover) VALUES 
                (:album_id, :album_name, :artist_name, :artist_id, :release_date, :cover)
                ON CONFLICT (album_id) DO NOTHING""",
                album_data.model_dump()
        )

    albums = await database.fetch_all(
        "SELECT * FROM albums WHERE album_name = :album_name",
        {'album_name': album_name}
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

#FOR THE MOMENT, WHERE WE NEED USER_ID WE WILL GET IT FROM THE PYDANTIC MODEL
#LATER, WHEN WE HAVE AUTH, WE WILL DO IT WITH Depends(get_current_user)

@app.post("/album/{album_id}/rating")
async def rate_album(album_id: str, review: ReviewCreate, response: Response): #review is an object of the ReviewCreate Pydantic class

    success, message = await review_manager.add_review(review.user_id, album_id, review.rating, review.review)
    #add_review has async calls, and this call should also be await

    response.status_code = (status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)

    return {"message": message} #fastapi automatically serializes this to json


@app.delete("/album/{album_id}/delete_rating")
async def delete_rate(album_id: str, delete: ReviewDelete, response: Response):

    success, message =  await review_manager.delete_review(delete.user_id, album_id)

    response.status_code = (status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)

    return {"message": message}


# FAVORITES FUNCTION

@app.post("/album/{album_id}/add_favorite")
async def add_to_favorites(album_id, add: FavoriteCreate, response: Response):

    success, message = await user_manager.add_favourite(add.user_id, album_id)
    response.status_code = response.status_code = (status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)

    return {"message": message}


@app.get("/user/{user_id}/get_favorites", response_model=list[FavoritesOut], status_code=status.HTTP_200_OK)
async def get_user_favorites(user_id: int):

    favorites = await user_manager.get_favorites(user_id)

    favorites_list: list[FavoritesOut] = []
    for row in favorites:
        favorites_list.append(row)

    return favorites_list


# FOLLOWERS FUNCTIONS
@app.post("/user/{followed_username}/follow")
async def follow(followed_username: str, follow: FollowerCreate, response: Response):

    follower_id = follow.user_id

    if not follower_id:

        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "User has to be logged in"}

    followed_id = await database.fetch_one("SELECT id FROM users WHERE username = :username", {'username': followed_username})

    success, message = await user_manager.follow_user(follower_id, followed_id)

    response.status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST

    return {"message": message}


@app.delete("/user/{followed_id}/unfollow")
async def unfollow(followed_id: int, follower: FollowDelete, response: Response):

    follower_id = follower.user_id

    if not follower_id:

        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "User has to be logged in"}

    success, message = await user_manager.unfollow_user(follower_id, followed_id)

    response.status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST

    return {"message": message}


@app.get("/user/{user_id}/get_followers", response_model=list[FollowersOut], status_code=status.HTTP_200_OK)
async def get_follower(user_id: int):
    followers = await user_manager.get_followers(user_id)
    followers_return : list[FollowersOut] = []
    for follower in followers:
        followers_return.append(follower)
    return followers_return


@app.get("/user/{user_id}/get_following", response_model=list[FollowingOut], status_code=status.HTTP_200_OK)
async def get_following(user_id):
    followings = await user_manager.get_following(user_id)
    followings_return: list[FollowingOut] = []
    for following in followings:
        followings_return.append(following)
    return followings_return

# USER PROFILE
@app.get("/user/{username}/profile", response_model=UserProfileOut)
async def get_profile(username, response: Response):

        user = await database.fetch_one(
            "SELECT id, username, bio, picture FROM users WHERE LOWER(username) = :username",
            {'username': username.lower()},
        )
        if not user:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"error": "User not found"}

        user_data = {
            "id": user["id"],
            "username": user["username"],
            "bio": user["bio"],
            "picture": user["picture"],
        }

        favorites = await database.fetch_all(
            """
            SELECT a.album_name as album_name, a.artist_name as artist_name, a.release_date as release_date, a.cover as cover
            FROM favorites f
            JOIN albums a ON f.album_id = a.album_id
            WHERE f.user_id = :user_id
        """,
            {'user_id': user_data["id"]}
        )
        user_data["favorites"] = favorites #we have favorites being a list[FavoritesOut] in the Pydantic model for UserProfileOut
        #if the key of the dict returned by the database (called favorites) in this case match the Pydantic model fields
        #(the fields of FavoritesOut in this case) the transition from dict to Pydantic model is automatically

        row = await database.fetch_one(
            "SELECT COUNT(*) as count FROM followers WHERE followed_id = :user_id", {'user_id': user_data["id"]}
        )
        user_data["followers_count"] = row['count']

        row = await database.fetch_one(
            "SELECT COUNT(*) as count FROM followers WHERE follower_id = :user_id", {'user_id': user_data["id"]}
        )
        user_data["following_count"] = row['count']

        reviews = await review_manager.get_user_reviews(user["id"])
        user_data["reviews"] = reviews #same as with favorites

        response.status_code = status.HTTP_200_OK
        return user_data #now the user_data dictionary matches the name of the keys with the fields of the Pydantic model and
        #the data types, so serialization is done by Fastapi


@app.get("/user/{user_id}/profile", response_model=UserProfileOut)
async def get_own_profile(user_id: int, response: Response):

        user = await database.fetch_one(
            "SELECT id, username, bio, picture FROM users WHERE id = :user_id", {'user_id': user_id}
        )
    
        if not user:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"error": "User not found"}

        favorites = await database.fetch_all(
            """
            SELECT a.album_name as album_name, a.artist_name as artist_name, a.release_date as release_date, a.cover as cover
            FROM favorites f
            JOIN albums a ON f.album_id = a.album_id
            WHERE f.user_id = :user_id
        """,
            {'user_id': user['id']}
        )
    
        user["favorites"] = favorites

        row = await database.fetch_one(
            "SELECT COUNT(*) as count FROM followers WHERE followed_id = :user_id", {'user_id': user['id']}
        )
        user["followers_count"] = row['count']

        row = await database.fetch_one(
            "SELECT COUNT(*) as count FROM followers WHERE follower_id = :user_id", {'user_id': user['id']}
        )
        user["following_count"] = row['count']

        reviews = await review_manager.get_user_reviews(user['id'])
        user["reviews"] = reviews

        response.status_code = status.HTTP_200_OK
        return user


@app.get("/user/{user_id}/friends_activity", response_model=list[ActivityOut])
async def friends_activity(user_id: int, response: Response):

    recent_activity = await review_manager.friends_recent_activity(user_id)

    response.status_code = status.HTTP_200_OK
    return recent_activity


@app.put("/user/{user_id}/update_bio")
async def update_bio(user_id: int, bio: BioUpdate, response: Response):

    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "User not logged in"}

    bio_text = bio.bio 

    await database.execute("UPDATE users SET bio = :bio WHERE id = :id", {'bio': bio_text, 'id': user_id})

    response.status_code = status.HTTP_200_OK
    return {"message": "Bio successfully updated"}


@app.put("/user/{user_id}/update_picture")
async def update_picture(user_id: int, picture: PictureUpdate, response: Response):

    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "User not logged in"}

    picture_url = picture.picture

    await database.execute("UPDATE users SET picture = :picture WHERE id = :id", {'picture': picture_url, 'id': user_id})
    response.status_code = status.HTTP_200_OK

    return {"message": "Profile picture successfully updated"}


# RECOMANDATION ENGINE


@app.route("/user/get_recommendations", methods=["GET"])
def get_recommendations():

    full_recommendations_list = []
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    with user_manager.connect() as conn:

        cursor = conn.cursor()
        cursor.execute(
            "SELECT album_id FROM recomandations WHERE user_id = ? ORDER BY RANDOM() LIMIT 10",
            (user_id,),
        )
        recommendations = cursor.fetchall()
        recommendations_list = [album[0] for album in recommendations]
        for album_id in recommendations_list:

            cursor.execute(
                "SELECT album_name, artist_name, release_date, cover FROM albums WHERE album_id = ?",
                (album_id,),
            )
            row = cursor.fetchone()
            album_data = {
                "album_name": row[0],
                "artist_name": row[1],
                "release_date": row[2],
                "cover": row[3],
            }
            full_recommendations_list.append(album_data)

    return jsonify({"recommendations": full_recommendations_list})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
