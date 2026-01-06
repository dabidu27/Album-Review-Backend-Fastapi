import asyncio
from databases import Database
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
database = Database(DATABASE_URL)

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    bio TEXT DEFAULT '',
    picture TEXT DEFAULT ''
);
"""

CREATE_ALBUMS_TABLE = """
CREATE TABLE IF NOT EXISTS albums (
    album_id TEXT PRIMARY KEY,
    album_name TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    release_date DATE NOT NULL,
    cover TEXT NOT NULL
);
"""

CREATE_REVIEWS_TABLE = """
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 0 AND 5),
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE,
    UNIQUE (user_id, album_id)
);
"""

CREATE_FAVORITES_TABLE = """
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE,
    UNIQUE (user_id, album_id)
);
"""

CREATE_FOLLOWERS_TABLE = """
CREATE TABLE IF NOT EXISTS followers (
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (followed_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (follower_id, followed_id)
);
"""

CREATE_RECOMMENDATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    album_id TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE,
    UNIQUE (user_id, album_id)
);
"""


async def main():

    await database.connect()

    await database.execute(CREATE_USERS_TABLE)
    await database.execute(CREATE_ALBUMS_TABLE)
    await database.execute(CREATE_REVIEWS_TABLE)
    await database.execute(CREATE_FAVORITES_TABLE)
    await database.execute(CREATE_FOLLOWERS_TABLE)
    await database.execute(CREATE_RECOMMENDATIONS_TABLE)

    await database.disconnect()
