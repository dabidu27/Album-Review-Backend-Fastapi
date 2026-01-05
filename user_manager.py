import sqlite3
from spotify import (
    get_spotify_token,
    search_for_album_by_id,
    search_for_artist_albums,
    search_related_artists,
)
from init_db import database


class UserManager:

    # FAVORITES FUNCTIONS
    async def add_favourite(self, user_id, album_id):

        row = await database.fetch_one(
            "SELECT COUNT(*) as count FROM favorites WHERE user_id = :user_id",
            {"user_id": int(user_id)},
        )

        if row["count"] == 3:

            return False, "You can have only 3 favorites"

        else:
            albums = await database.fetch_all(
                "SELECT album_id FROM favorites WHERE user_id = :user_id",
                {"user_id": int(user_id)},
            )
            for album in albums:
                if album_id == album["album_id"]:
                    return False, "Already added to favorites"
            await database.execute(
                "INSERT INTO favorites (user_id, album_id) VALUES (:user_id, :album_id)",
                {"user_id": int(user_id), "album_id": album_id},
            )
            return True, "Album added to favorites"

    async def get_favorites(self, user_id):

        albums = await database.fetch_all(
            "SELECT album_id FROM favorites WHERE user_id = :user_id",
            {"user_id": int(user_id)},
        )

        return albums

    # FOLLOWERS FUNCTIONS
    async def follow_user(self, follower_id, followed_id):

        if follower_id == followed_id:
            return False, "You cannot follow yourself"

        try:

            await database.execute(
                "INSERT INTO followers (follower_id, followed_id) VALUES (:follower_id, :followed_id)",
                {
                    "follower_id": follower_id,
                    "followed_id": followed_id,
                },
            )
            return True, "User followed successfully"

        except Exception:

            return False, "You already follow this user"

    async def unfollow_user(self, follower_id, followed_id):

        await database.execute(
            "DELETE FROM followers WHERE follower_id = :follower_id AND followed_id = :followed_id",
            {"follower_id": follower_id, "followed_id": followed_id},
        )

        return True, "Successfully unfollowed user"

    async def get_followers(self, user_id):

        rows = await database.fetch_all(
            """
                SELECT u.id as id, u.username as username
                FROM followers f
                JOIN users u
                ON f.follower_id = u.id
                WHERE f.followed_id = :user_id
            """,
            {"user_id": int(user_id)},
        )

        followers = [{"id": row["id"], "username": row["username"]} for row in rows]

        return followers

    async def get_following(self, user_id):

        rows = await database.fetch_all(
            """
                SELECT u.id as id, u.username as username
                FROM followers f
                JOIN users u
                ON f.followed_id = u.id
                WHERE f.follower_id = :user_id
            """,
            {"user_id": int(user_id)},
        )

        following = [{"id": row["id"], "username": row["username"]} for row in rows]

        return following

    # RECOMANDATION ENGINE

    async def other_albums_by_artist(self):

        token = get_spotify_token()

        rows = await database.fetch_all(
            """
            SELECT r.album_id, r.user_id, a.artist_name
            FROM reviews r
            JOIN albums a ON r.album_id = a.album_id
            WHERE r.rating >= 3
            """
        )

        for row in rows:

            album_id = row["album_id"]
            user_id = row["user_id"]
            artist_name = row["artist_name"]

            artist_albums = search_for_artist_albums(token, artist_name)

            for album in artist_albums:

                artist_album_id = album["id"]

                if artist_album_id == album_id:
                    continue

                # Insert recommendation
                await database.execute(
                    """
                    INSERT OR IGNORE INTO recomandations (user_id, album_id)
                    VALUES (:user_id, :album_id)
                    """,
                    {
                        "user_id": user_id,
                        "album_id": artist_album_id,
                    },
                )

                # Check if album already exists
                existing_album = await database.fetch_one(
                    "SELECT album_id FROM albums WHERE album_id = :album_id",
                    {"album_id": artist_album_id},
                )

                if existing_album:
                    continue

                # Fetch album from Spotify
                token = get_spotify_token()
                album_data = search_for_album_by_id(token, artist_album_id)

                # Insert album
                await database.execute(
                    """
                    INSERT INTO albums (
                        album_id,
                        album_name,
                        artist_name,
                        artist_id,
                        release_date,
                        cover
                    )
                    VALUES (
                        :album_id,
                        :album_name,
                        :artist_name,
                        :artist_id,
                        :release_date,
                        :cover
                    )
                    """,
                    {
                        "album_id": album_data["id"],
                        "album_name": album_data["name"],
                        "artist_name": album_data["artists"][0]["name"],
                        "artist_id": album_data["artists"][0]["id"],
                        "release_date": album_data["release_date"],
                        "cover": album_data["images"][0]["url"],
                    },
                )

    async def albums_by_similar_artists(self):

        token = get_spotify_token()

        rows = await database.fetch_all(
            """
            SELECT r.album_id, r.user_id, a.artist_name
            FROM reviews r
            JOIN albums a ON r.album_id = a.album_id
            WHERE r.rating >= 3
            """
        )

        for row in rows:

            album_id = row["album_id"]
            user_id = row["user_id"]
            artist_name = row["artist_name"]

            related_artists = search_related_artists(token, artist_name)

            for related_artist in related_artists:

                related_artist_name = related_artist["name"]

                related_artist_albums = search_for_artist_albums(
                    token, related_artist_name
                )

                for album in related_artist_albums:

                    related_artist_album_id = album["id"]

                    if related_artist_album_id == album_id:
                        continue

                    await database.execute(
                        """
                        INSERT OR IGNORE INTO recomandations (user_id, album_id)
                        VALUES (:user_id, :album_id)
                        """,
                        {
                            "user_id": user_id,
                            "album_id": related_artist_album_id,
                        },
                    )

                    existing_album = await database.fetch_one(
                        "SELECT album_id FROM albums WHERE album_id = :album_id",
                        {"album_id": related_artist_album_id},
                    )

                    if existing_album:
                        continue

                    token = get_spotify_token()
                    album_data = search_for_album_by_id(token, related_artist_album_id)

                    await database.execute(
                        """
                        INSERT INTO albums (
                            album_id,
                            album_name,
                            artist_name,
                            artist_id,
                            release_date,
                            cover
                        )
                        VALUES (
                            :album_id,
                            :album_name,
                            :artist_name,
                            :artist_id,
                            :release_date,
                            :cover
                        )
                        """,
                        {
                            "album_id": album_data["id"],
                            "album_name": album_data["name"],
                            "artist_name": album_data["artists"][0]["name"],
                            "artist_id": album_data["artists"][0]["id"],
                            "release_date": album_data["release_date"],
                            "cover": album_data["images"][0]["url"],
                        },
                    )

    async def collaborative_filtering(self):

        rows = await database.fetch_all(
            """
            SELECT album_id, user_id
            FROM reviews
            WHERE rating >= 3
            """
        )

        for row in rows:

            album_id = row["album_id"]
            user_id = row["user_id"]

            other_users = await database.fetch_all(
                """
                SELECT DISTINCT user_id
                FROM reviews
                WHERE rating >= 3
                AND album_id = :album_id
                AND user_id != :user_id
                """,
                {
                    "album_id": album_id,
                    "user_id": user_id,
                },
            )

            for other_user in other_users:

                other_user_id = other_user["user_id"]

                albums_to_recommend = await database.fetch_all(
                    """
                    SELECT album_id
                    FROM reviews
                    WHERE user_id = :other_user_id
                    AND rating >= 3
                    """,
                    {"other_user_id": other_user_id},
                )

                for album in albums_to_recommend:

                    await database.execute(
                        """
                        INSERT OR IGNORE INTO recomandations (user_id, album_id)
                        VALUES (:user_id, :album_id)
                        """,
                        {
                            "user_id": user_id,
                            "album_id": album["album_id"],
                        },
                    )
