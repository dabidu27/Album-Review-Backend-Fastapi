from dotenv import load_dotenv
import os
import base64
import requests

load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


def get_spotify_token():

    url = "https://accounts.spotify.com/api/token"

    id = CLIENT_ID + ":" + CLIENT_SECRET
    id_encoded = id.encode("utf-8")
    id_encoded_base64 = str(base64.b64encode(id_encoded), "utf-8")

    headers = {
        "Authorization": f"Basic {id_encoded_base64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post(url, data=data, headers=headers)

    json_result = response.json()
    token = json_result["access_token"]

    return token


def search_for_artist_id(token, artist_name):

    url = "https://api.spotify.com/v1/search"

    headers = {"Authorization": f"Bearer {token}"}

    params = {"q": artist_name, "type": "artist", "limit": "1"}

    response = requests.get(url, params=params, headers=headers)

    json_result = response.json()

    artist_items = json_result["artists"]["items"]
    artist_items = artist_items[0]

    artist_id = artist_items["id"]

    return artist_id


def search_for_artist_albums(token, artist_name):

    artist_id = search_for_artist_id(token, artist_name)

    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"

    headers = {"Authorization": f"Bearer {token}"}

    params = {"include_groups": "album"}

    response = requests.get(url, headers=headers, params=params)

    json_result = response.json()

    albums = json_result["items"]

    return albums


def search_for_album(token, album_name):

    url = "https://api.spotify.com/v1/search"

    headers = {"Authorization": f"Bearer {token}"}

    params = {"q": album_name, "type": "album", "limit": 1}

    response = requests.get(url, headers=headers, params=params)

    json_result = response.json()

    album = json_result["albums"]["items"][0]

    return album


def search_for_album_by_id(token, album_id):

    url = "https://api.spotify.com/v1/albums"

    headers = {"Authorization": f"Bearer {token}"}
    params = {"ids": {album_id}}

    response = requests.get(url, headers=headers, params=params)

    album = response.json()

    return album["albums"][0]


def search_related_artists(token, artist_name):

    artist_id = search_for_artist_id(token, artist_name)

    if not artist_id:
        print(f"Artist not found: {artist_name}")
        return []

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"https://api.spotify.com/v1/artists/{artist_id}/related-artists",
        headers=headers,
    )

    json_result = response.json()

    artists = json_result.get("artists", [])
    return artists
