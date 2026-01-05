from user_manager import UserManager
from review_manager import ReviewManager
import os
from spotify import get_spotify_token, search_for_artist_albums, search_for_album
from datetime import datetime, timedelta
from dotenv import load_dotenv
from init_db import database
from fastapi import FastAPI, status, Response
from models import AlbumOut, ReviewCreate, ReviewDelete, FavoriteCreate, FollowerCreate, FavoritesOut, FollowDelete, FollowersOut


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
async def follower(user_id: int):
    followers = await user_manager.get_followers(user_id)
    followers_return : list[FollowersOut] = []
    for follower in followers:
        followers_return.append(follower)
    return followers_return


@app.route("/user/<user_id>/get_following", methods=["GET"])
def following(user_id):
    following = user_manager.get_following(user_id)
    return jsonify(following)


# USER PROFILE
@app.route("/user/<username>/profile", methods=["GET"])
def get_profile(username):
    with user_manager.connect() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, bio, picture FROM users WHERE LOWER(username) = ?",
            (username.lower(),),
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_data = {
            "id": user[0],
            "username": user[1],
            "bio": user[2],
            "picture": user[3],
        }

        cursor.execute(
            """
            SELECT a.album_name, a.artist_name, a.release_date, a.cover
            FROM favorites f
            JOIN albums a ON f.album_id = a.album_id
            WHERE f.user_id = ?
        """,
            (user_data["id"],),
        )
        favorites = cursor.fetchall()
        user_data["favorites"] = [
            {
                "album_name": fav[0],
                "artist_name": fav[1],
                "release_date": fav[2],
                "cover": fav[3],
            }
            for fav in favorites
        ]

        cursor.execute(
            "SELECT COUNT(*) FROM followers WHERE followed_id = ?", (user_data["id"],)
        )
        user_data["followers_count"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM followers WHERE follower_id = ?", (user_data["id"],)
        )
        user_data["following_count"] = cursor.fetchone()[0]

        reviews = review_manager.get_user_reviews(user[0])
        user_data["reviews"] = reviews

        return jsonify(user_data)


@app.route("/user/profile", methods=["GET"])
def get_own_profile():

    user_id = session.get("user_id")

    with user_manager.connect() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, bio, picture FROM users WHERE id = ?", (user_id,)
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_data = {
            "id": user[0],
            "username": user[1],
            "bio": user[2],
            "picture": user[3],
        }

        cursor.execute(
            """
            SELECT a.album_name, a.artist_name, a.release_date, a.cover
            FROM favorites f
            JOIN albums a ON f.album_id = a.album_id
            WHERE f.user_id = ?
        """,
            (user_data["id"],),
        )
        favorites = cursor.fetchall()
        user_data["favorites"] = [
            {
                "album_name": fav[0],
                "artist_name": fav[1],
                "release_date": fav[2],
                "cover": fav[3],
            }
            for fav in favorites
        ]

        cursor.execute(
            "SELECT COUNT(*) FROM followers WHERE followed_id = ?", (user_data["id"],)
        )
        user_data["followers_count"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM followers WHERE follower_id = ?", (user_data["id"],)
        )
        user_data["following_count"] = cursor.fetchone()[0]

        reviews = review_manager.get_user_reviews(user[0])
        user_data["reviews"] = reviews

        return jsonify(user_data)


@app.route("/user/friends_activity")
def friends_activity():

    user_id = session.get("user_id")
    recent_activity = review_manager.friends_recent_activity(user_id)

    recent_activity_list = []

    for activity in recent_activity:
        recent_activity_list.append(
            {
                "album_name": activity[0],
                "artist_name": activity[1],
                "cover": activity[2],
                "rating": activity[3],
                "review": activity[4],
            }
        )

    return jsonify({"recent_activity": recent_activity_list})


@app.route("/user/update_bio", methods=["POST"])
def update_bio():

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    data = request.json
    bio = data.get("bio", "")

    with user_manager.connect() as conn:

        cursor = conn.cursor()
        cursor.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
        conn.commit()

    return jsonify({"message": "Bio successfully updated"}), 200


@app.route("/user/update_picture", methods=["POST"])
def update_picture():

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    data = request.json
    picture = data.get("picture", "")

    with user_manager.connect() as conn:

        cursor = conn.cursor()
        cursor.execute("UPDATE users SET picture = ? WHERE id = ?", (picture, user_id))
        conn.commit()

    return jsonify({"message": "Profile picture successfully updated"}), 200


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
