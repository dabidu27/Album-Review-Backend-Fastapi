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

        existing = await database.fetch_one(
            "select * from reviews where user_id = :user_id and album_id = :album_id",
            {"user_id": int(user_id), "album_id": album_id},
        )
        if not existing:
            return False, "Review not found"

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

    async def get_user_reviews(self, user_id):

        reviews = await database.fetch_all(
            "SELECT a.album_name, a.artist_name, a.cover, r.rating, r.review FROM reviews r JOIN albums a ON r.album_id = a.album_id WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        return reviews

    async def friends_recent_activity(self, user_id):

        query = """
        SELECT
    a.album_name,
    a.artist_name,
    a.cover,
    r.rating,
    r.review
FROM followers f
JOIN reviews r ON r.user_id = f.followed_id
JOIN albums a ON a.album_id = r.album_id
WHERE f.follower_id = :user_id
  AND COALESCE(r.updated_at, r.created_at) >= NOW() - INTERVAL '7 days'
ORDER BY COALESCE(r.updated_at, r.created_at) DESC
        """

        return await database.fetch_all(query, {"user_id": user_id})
