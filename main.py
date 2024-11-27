import os
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re
import subprocess
from pytz import timezone  
import pytz
import jwt
import configparser
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def log_section(title):
    print(f"{Style.BRIGHT}{Fore.MAGENTA}{'='*40}")
    print(f"{Style.BRIGHT}{Fore.CYAN}{title}")
    print(f"{Style.BRIGHT}{Fore.MAGENTA}{'='*40}")

def log_info(message):
    print(f"{Fore.GREEN}[INFO] {Style.RESET_ALL}{message}")

def log_warning(message):
    print(f"{Fore.YELLOW}[WARNING] {Style.RESET_ALL}{message}")

def log_error(message):
    print(f"{Fore.RED}[ERROR] {Style.RESET_ALL}{message}")

def log_success(message):
    print(f"{Fore.BLUE}[SUCCESS] {Style.RESET_ALL}{message}")

# Load Configuration
log_section("Loading Configuration")
config = configparser.ConfigParser()
config.read("config.ini")
schedule_interval_hours = int(config.get("SETTINGS", "schedule_interval_hours", fallback=2))
log_info("Configuration loaded successfully.")

# Settings
base_url = config["Server"]["base_url"]
rtmp_base_url = config["Server"]["rtmp_base_url"]
server_url = config["Server"]["server_url"]
secret_key = config["API"]["secret_key"]
scopes = config["API"]["scopes"].split(",")
local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
now_utc = datetime.now(pytz.utc)
payload = {
    "aud": "LiveApp",
    "sub": "token",
    "iat": now_utc,
}
api_key = jwt.encode(payload, secret_key, algorithm="HS256")
log_info(f"JWT for Ant Media Server generated")

log_section("Authenticating with YouTube API")
flow = InstalledAppFlow.from_client_secrets_file("credentials_oauth.json", scopes)
credentials = flow.run_local_server(port=0)
youtube = build("youtube", "v3", credentials=credentials)
log_success("YouTube API authentication successful.")

def load_stream_titles(filename="stream_titles.xlsx"):
    log_info(f"Loading stream titles from {filename}...")
    try:
        df_titles = pd.read_excel(filename)
        log_success("Stream titles loaded successfully.")
        return df_titles["name"].tolist()
    except Exception as e:
        log_error(f"Failed to load stream titles: {e}")
        return []

def parse_video_name(video_name):
    match = re.search(r"video(\d{2})del(\d{2})numero(\d+)", video_name)
    if match:
        day = int(match.group(1))  # Día
        month = int(match.group(2))  # Mes
        video_num = int(match.group(3))  # Número del video
        return day, month, video_num
    return None, None, None

def generate_videos_from_files():
    log_section("Generating Videos from Files")
    log_info("Reading videos from the 'videos/' folder...")
    videos = []
    video_files = [f for f in os.listdir('videos') if f.startswith("video") and f.endswith(".mp4")]
    video_files.sort()

    grouped_videos = {}

    # Agrupar videos correctamente por día y mes
    for video_file in video_files:
        video_name, _ = os.path.splitext(video_file)
        day, month, video_num = parse_video_name(video_name)
        if day and month and video_num:
            video_url = f"{base_url}{video_file}"
            date_key = f"{day:02}-{month:02}"  # Clave única por día y mes
            if date_key not in grouped_videos:
                grouped_videos[date_key] = []
            grouped_videos[date_key].append({
                "Video Name": video_name,
                "Number": video_num,
                "Video URL": video_url,
                "Month": month,
                "Day": day,
                "Video Number": video_num,
            })

    log_info("Videos grouped by day and month:")
    for date_key, video_list in grouped_videos.items():
        log_info(f"  - {date_key}: {[v['Video Name'] for v in video_list]}")

    # Asignar horarios incrementalmente dentro del día
    for date_key, video_list in grouped_videos.items():
        video_list.sort(key=lambda v: v["Video Number"])  # Ordenar por número de video
        day, month = map(int, date_key.split('-'))
        base_time = datetime(datetime.now().year, month, day, 5, 30)  # Hora inicial del día
        log_info(f"\nAssigning schedules for {date_key} (starting from {base_time}):")
        for i, video in enumerate(video_list):
            start_time = base_time + timedelta(hours=i * schedule_interval_hours)
            video["Start Time"] = start_time
            log_info(f"  - {video['Video Name']} -> {start_time}")
            videos.append(video)

    log_success(f"Total videos processed: {len(videos)}")
    return videos


def create_stream_key(video_name):
    log_section(f"Creating Stream Key for {video_name}")
    request = youtube.liveStreams().insert(
        part="snippet,cdn",
        body={
            "snippet": {"title": video_name},
            "cdn": {
                "resolution": "1080p",
                "ingestionType": "rtmp",
                "frameRate": "30fps",
            }
        }
    )
    response = request.execute()
    stream_id = response["id"]
    stream_key = response["cdn"]["ingestionInfo"]["streamName"]
    log_success(f"Stream key created: {stream_key} (ID: {stream_id})")
    return stream_id, stream_key

def generate_thumbnail_ffmpeg(video_path, video_name, output_folder="images"):
    log_section(f"Generating Thumbnail for {video_name}")
    os.makedirs(output_folder, exist_ok=True)
    thumbnail_path = os.path.join(output_folder, f"{video_name}_thumbnail.jpg")
    command = [
        "ffmpeg", "-i", video_path, "-ss", "00:00:02", "-vframes", "1", thumbnail_path, "-y"
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_success(f"Thumbnail generated: {thumbnail_path}")
    except subprocess.CalledProcessError as e:
        log_error(f"Error generating thumbnail for {video_path}: {e}")
        thumbnail_path = None
    return thumbnail_path


def create_youtube_event(title, start_time, stream_id, stream_key, thumbnail_path):
    log_section(f"Creating YouTube Event: {title}")

    local_tz = timezone('America/Argentina/Buenos_Aires')
    start_time_local = local_tz.localize(start_time)
    start_time_utc = start_time_local.astimezone(timezone('UTC'))

    try:
        log_info("Sending request to YouTube API for live event creation...")
        request = youtube.liveBroadcasts().insert(
            part="snippet,status,contentDetails",
            body={
                "snippet": {
                    "title": title,
                    "categoryId": 10,
                    "scheduledStartTime": start_time_utc.isoformat()
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                },
                "contentDetails": {
                    "enableAutoStart": True,
                    "enableAutoStop": True,
                }
            }
        )
        response = request.execute()
        broadcast_id = response["id"]
        log_success(f"Live broadcast event created with ID: {broadcast_id}")

        log_info(f"Linking stream key '{stream_id}' to the event...")
        request = youtube.liveBroadcasts().bind(
            part="id,contentDetails",
            id=broadcast_id,
            streamId=stream_id
        )
        request.execute()
        log_success(f"Stream key successfully linked to event '{broadcast_id}'.")

        upload_thumbnail(broadcast_id, thumbnail_path)

        log_success(f"YouTube event created and thumbnail uploaded for '{title}'.")
    except Exception as e:
        log_error(f"Error creating YouTube event: {e}")

def upload_thumbnail(broadcast_id, thumbnail_path):
    if not thumbnail_path:
        log_warning("No thumbnail path provided. Skipping thumbnail upload.")
        return

    log_section(f"Uploading Thumbnail for Event ID: {broadcast_id}")
    try:
        request = youtube.thumbnails().set(
            videoId=broadcast_id,
            media_body=thumbnail_path
        )
        request.execute()
        log_success(f"Thumbnail successfully uploaded for event {broadcast_id}.")
    except Exception as e:
        log_error(f"Error uploading thumbnail for event {broadcast_id}: {e}")


def create_playlist_ant_media(video_url, video_name, start_time, rtmp_url):
    log_section(f"Creating Playlist in Ant Media Server for {video_name}")

    file_name = os.path.splitext(os.path.basename(video_url))[0]

    if start_time.tzinfo is None:
        local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        start_time = local_tz.localize(start_time)

    planned_start_date_unix = int(start_time.astimezone(pytz.utc).timestamp())
    log_info(f"Planned Start Date (UNIX timestamp in seconds): {planned_start_date_unix}")

    playlist = {
        "name": video_name,
        "streamId": file_name,
        "playListItemList": [
            {
                "name": video_name,
                "streamUrl": video_url
            }
        ],
        "currentPlayIndex": 0,
        "playlistLoopEnabled": False,
        "status": "created",
        "type": "playlist",
        "plannedStartDate": planned_start_date_unix,
        "rtmpURL": rtmp_url
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"{api_key}"
    }

    try:
        response = requests.post(
            f"{server_url}/LiveApp/rest/v2/broadcasts/create",
            headers=headers,
            data=json.dumps(playlist)
        )

        if response.status_code == 200:
            log_success(f"Playlist successfully created in Ant Media Server for '{video_name}' with RTMP URL '{rtmp_url}'.")
        else:
            log_error(f"Error creating playlist: {response.status_code} - {response.text}")
    except Exception as e:
        log_error(f"Error sending request to Ant Media Server: {e}")


log_section("Processing Videos and Creating Playlists")

stream_titles = load_stream_titles()
schedule_data = []

videos = generate_videos_from_files()
log_info(f"Total videos to process: {len(videos)}")

for i, video in enumerate(videos):
    log_section(f"Processing Video {i + 1}/{len(videos)}: {video['Video Name']}")
    
    title_for_youtube = stream_titles[i] if i < len(stream_titles) else f"Stream {i + 1}"
    log_info(f"YouTube Title: {title_for_youtube}")
    
    start_time = video["Start Time"]
    log_info(f"Scheduled Start Time: {start_time}")

    stream_id, stream_key = create_stream_key(video["Video Name"])
    video_path = os.path.join("videos", f"{video['Video Name']}.mp4")
    thumbnail_path = generate_thumbnail_ffmpeg(video_path, video["Video Name"])

    create_youtube_event(title_for_youtube, start_time, stream_id, stream_key, thumbnail_path)
    
    create_playlist_ant_media(video["Video URL"], video["Video Name"], start_time, f"{rtmp_base_url}{stream_key}")

    schedule_data.append({
        "Video Name": video["Video Name"],
        "YouTube Title": title_for_youtube,
        "Start Time": start_time.strftime('%Y-%m-%d %H:%M'),
        "Video URL": video["Video URL"],
        "RTMP URL": f"{rtmp_base_url}{stream_key}"
    })

    log_success(f"Finished processing video {video['Video Name']}.")

# Save schedule to an Excel file
log_section("Saving Schedule")
try:
    df = pd.DataFrame(schedule_data)
    df.to_excel("playlist_schedule_example.xlsx", index=False)
    log_success("Schedule saved successfully to 'playlist_schedule_example.xlsx'.")
except Exception as e:
    log_error(f"Error saving schedule to Excel: {e}")
