import sqlite3
from init_db import database


class ReviewManager:

    async def add_review(self, user_id, album_id, rating, review):

        row = await database.fetch_one(
            "SELECT * FROM reviews WHERE user_id = :user_id AND album_id = :album_id",
            {"user_id": int(user_id), "album_id": album_id},
        )

        if row:

            await database.execute(
                """
                    UPDATE reviews
                    SET rating = :rating, review = :review, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND album_id = :album_id
                    """,
                {
                    "rating": rating,
                    "review": review,
                    "user_id": int(user_id),
                    "album_id": album_id,
                },
            )
        else:

            await database.execute(
                """
                    INSERT INTO reviews (user_id, album_id, rating, review, created_at)
                    VALUES (:user_id, :album_id, :rating, :review, CURRENT_TIMESTAMP)
                    """,
                {
                    "rating": rating,
                    "review": review,
                    "user_id": int(user_id),
                    "album_id": album_id,
                },
            )

        return True, "Review added successfully"

    async def delete_review(self, user_id, album_id):

        await database.execute(
            "DELETE FROM reviews WHERE user_id = :user_id AND album_id = :album_id",
            {"user_id": int(user_id), "album_id": album_id},
        )

        return True, "Review deleted"

    def get_reviews_for_album(self, album_id):

        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT r.rating, r.review FROM reviews WHERE album_id = ?", (album_id,)
            )
            return cursor.fetchall()

    def get_user_reviews(self, user_id):

        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT a.album_name, a.artist_name, a.cover, r.rating, r.review FROM reviews r JOIN albums a ON r.album_id = a.album_id WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchall()

    def friends_recent_activity(self, user_id):

        recent_activity = []
        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT followed_id FROM followers WHERE follower_id = ?", (user_id,)
            )
            friends = cursor.fetchall()
            friends = [id[0] for id in friends]

            for friend_id in friends:

                cursor.execute(
                    """
                    SELECT a.album_name, a.artist_name, a.cover, r.rating, r.review FROM reviews r JOIN albums a ON r.album_id = a.album_id WHERE r.user_id = ?
                    AND COALESCE(r.updated_at, r.created_at) >= datetime('now', '-7 days')
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    """,
                    (friend_id,),
                )
                recent_activity.extend(cursor.fetchall())

        return recent_activity
