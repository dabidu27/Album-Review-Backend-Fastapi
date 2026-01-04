import sqlite3
from spotify import (
    get_spotify_token,
    search_for_album_by_id,
    search_for_artist_albums,
    search_related_artists,
)
from init_db import database


class UserManager:

    # REGISTER, LOGIN
    def register_user(self, username, password):

        password_hash = generate_password_hash(password)

        try:

            with self.connect() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO USERS (username, password_hash) VALUES" "(?, ?)",
                    (username, password_hash),
                )

                conn.commit()

            return True, "User registered successfully"

        except sqlite3.IntegrityError:
            return False, "Username already exists"

    def login_user(self, username, password):

        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username, password_hash FROM users WHERE username == ?",
                (username,),
            )

            row = cursor.fetchone()

        if row is None:

            return False, "User not found", None

        password_hash = row[2]

        if check_password_hash(password_hash, password):

            return True, "Successful login", row[0]
        else:
            return False, "Wrong password", None

    def change_user_password(self, username, new_password):

        password_hash = generate_password_hash(new_password)

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if not user:
                return False, "User not found", None

            user_id = user[0]
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                return False, "User not found"
            return True, "Password updated successfully"

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

    def get_followers(self, user_id):

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.username
                FROM followers f
                JOIN users u
                ON f.follower_id = u.id
                WHERE f.follower_id = ?
            """,
                (int(user_id),),
            )

            rows = cursor.fetchall()

            followers = [{"id": row[0], "username": row[1]} for row in rows]

            return followers

    def get_following(self, user_id):

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.username
                FROM followers f
                JOIN users u
                ON f.followed_id = u.id
                WHERE f.followed_id = ?
            """,
                (int(user_id),),
            )

            rows = cursor.fetchall()

            following = [{"id": row[0], "username": row[1]} for row in rows]

            return following

    # RECOMANDATION ENGINE

    def other_albums_by_artist(self):

        token = get_spotify_token()

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute("SELECT album_id, user_id FROM reviews WHERE rating >= 3")

            rows = cursor.fetchall()

            for row in rows:

                id_album = row[0]
                user_id = row[1]

                cursor.execute(
                    "SELECT a.artist_name FROM reviews r JOIN albums a ON r.album_id = a.album_id WHERE a.album_id = ?",
                    (id_album,),
                )
                artist = cursor.fetchone()[0]

                artist_albums = search_for_artist_albums(token, artist)

                for album in artist_albums:

                    artist_album_id = album["id"]

                    if artist_album_id != id_album:

                        cursor.execute(
                            "INSERT OR IGNORE INTO recomandations (user_id, album_id) VALUES (?, ?)",
                            (user_id, artist_album_id),
                        )
                        cursor.execute(
                            "SELECT album_id FROM albums where album_id = ?",
                            (artist_album_id,),
                        )
                        album = cursor.fetchone()
                        if not album:

                            token = get_spotify_token()
                            album = search_for_album_by_id(
                                token, artist_album_id
                            )  # returns a dictionary

                            album_id = album["id"]
                            album_name = album["name"]
                            artist_name = album["artists"][0]["name"]
                            artist_id = album["artists"][0]["id"]
                            release_date = album["release_date"]
                            cover = album["images"][0]["url"]
                            cursor.execute(
                                """
                                            INSERT INTO albums (album_id, album_name, artist_name, artist_id, release_date, cover) VALUES (?, ?, ?, ?, ?, ?)
                           """,
                                (
                                    album_id,
                                    album_name,
                                    artist_name,
                                    artist_id,
                                    release_date,
                                    cover,
                                ),
                            )
        conn.commit()

    def albums_by_similar_artists(self):

        token = get_spotify_token()

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute("SELECT album_id, user_id FROM reviews WHERE rating >= 3")

            rows = cursor.fetchall()

            for row in rows:

                album_id = row[0]
                user_id = row[1]

                cursor.execute(
                    "SELECT a.artist_name FROM reviews r JOIN albums a ON r.album_id = a.album_id WHERE a.album_id = ?",
                    (album_id,),
                )
                artist = cursor.fetchone()[0]

                related_artists = search_related_artists(token, artist)

                for artist in related_artists:

                    related_artist_name = artist["name"]
                    related_artist_albums = search_for_artist_albums(
                        token, related_artist_name
                    )
                    for album in related_artist_albums:

                        related_artist_album_id = album["id"]

                        if related_artist_album_id != album_id:

                            cursor.execute(
                                "INSERT OR IGNORE INTO recomandations (user_id, album_id) VALUES (?, ?)",
                                (user_id, related_artist_album_id),
                            )
                            cursor.execute(
                                "SELECT album_id FROM albums where album_id = ?",
                                (related_artist_album_id,),
                            )
                            album = cursor.fetchone()
                            if not album:

                                token = get_spotify_token()
                                album = search_for_album_by_id(
                                    token, related_artist_album_id
                                )  # returns a dictionary

                                album_id = album["id"]
                                album_name = album["name"]
                                artist_name = album["artists"][0]["name"]
                                artist_id = album["artists"][0]["id"]
                                release_date = album["release_date"]
                                cover = album["images"][0]["url"]
                                cursor.execute(
                                    """
                                                INSERT INTO albums (album_id, album_name, artist_name, artist_id, release_date, cover) VALUES (?, ?, ?, ?, ?, ?)
                            """,
                                    (
                                        album_id,
                                        album_name,
                                        artist_name,
                                        artist_id,
                                        release_date,
                                        cover,
                                    ),
                                )
            conn.commit()

    def collaborative_filtering(self):

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute("SELECT album_id, user_id FROM reviews WHERE rating >= 3")

            rows = cursor.fetchall()

            for row in rows:

                album_id = row[0]
                user_id = row[1]

                cursor.execute(
                    "SELECT DISTINCT user_id FROM reviews WHERE rating >= 3 AND album_id = ? AND user_id != ?",
                    (album_id, user_id),
                )
                other_users = cursor.fetchall()

                for other_user in other_users:

                    cursor.execute(
                        "SELECT album_id FROM reviews WHERE user_id = ? AND rating >= 3",
                        (other_user[0],),
                    )

                    albums_to_recommend = cursor.fetchall()

                    for album in albums_to_recommend:

                        cursor.execute(
                            "INSERT OR IGNORE INTO recomandations (user_id, album_id) VALUES (?, ?)",
                            (user_id, album[0]),
                        )

            conn.commit()
