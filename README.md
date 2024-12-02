# Automatic Scheduling of Videos for YouTube and Ant Media Server

This project automates the scheduling of streaming events on YouTube and the creation of playlists on Ant Media Server using a predefined set of videos. The YouTube events include automatically generated thumbnails, custom titles, and stream keys. Additionally, the schedule is saved in an Excel file for reference.

## Edit config.ini and Google credentials

Remove the `.sample` from the file name, then fill it in with the Ant Media Server key, URL, and port where you access Ant Media Server.

## Project Structure

- **videos/**: Folder containing the video files to be scheduled. The files must follow the naming format `videoXdelYYnumeroZ.mp4`, where:
  - `X` indicates the video number (1, 2, or 3) for a specific day.
  - `YY` indicates the month in two digits (e.g., `11` for November).
  - `Z` indicates the sequence of the video on that day.

- **stream_titles.xlsx**: Excel file with a list of custom names for the streaming events on YouTube. It should contain a column named `Name`, with each row representing a unique title for a video.

- **playlist_schedule_example.xlsx**: Output file generated by the script, recording the complete schedule, including RTMP URLs and start times for each video.

## Installation

1. Clone this repository or download the necessary files.
2. Create a virtual environment and activate it:
   ```bash
   python -m venv path\to\venv   
   path\to\venv\Scripts\activate
   ```

3. Install the project dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Make sure `requirements.txt` includes necessary packages such as `pandas`, `google-auth-oauthlib`, `google-api-python-client`, `moviepy`, `Pillow`, etc.

4. Configure YouTube credentials:
   - Access [Google Cloud Console](https://console.developers.google.com/), enable the YouTube API, and set up OAuth 2.0.
   - Download the `credentials_oauth.json` file and place it in the root directory of the project.

## Usage

### 1. Prepare Files

   - **Place videos**: Ensure the video files are in the `videos/` folder and that their names follow the format `videoXdelYYnumeroZ.mp4`.
   - **Upload videos to the server**: Create a folder within the LiveApp called videos and upload all videos following the same format as the local videos folder, as they are needed for playback.
   - **Configure event titles**: In `stream_titles.xlsx`, enter the event titles in the `Name` column. Make sure the number of titles is sufficient for all videos.


### 2. Run the Script

   To schedule the videos, run:
   ```bash
   python main.py
   ```

   - The script:
     1. Authenticates the YouTube API to allow event creation and thumbnail upload.
     2. Reads the event titles from `stream_titles.xlsx`.
     3. Processes each video file in `videos/`, automatically assigning the month and day based on the file name.
     4. Generates stream keys, thumbnails, and creates streaming events on YouTube.
     5. Creates playlists on Ant Media Server and assigns the corresponding RTMP URLs.
     6. Saves the complete schedule in `playlist_schedule_example.xlsx`.

### 3. Review and Monitor

   - Check YouTube for the created events with the scheduled titles, thumbnails, and times.
   - On Ant Media Server, verify that the playlists are configured with the correct RTMP URLs.
   - Review `playlist_schedule_example.xlsx` to confirm the schedule and details of each video.

## Workflow Summary

1. **Data Preparation**  
   - Place videos in `videos/`
   - Create `stream_titles.xlsx` with titles

2. **Authentication and Data Reading**  
   - Authenticate YouTube API
   - Load titles from `stream_titles.xlsx`

3. **Video Processing**  
   - Read videos
   - Detect month and day
   - Assign start times

4. **YouTube Event Creation**  
   - Generate stream key
   - Create event with title
   - Upload thumbnail
   - Link stream key

5. **Playlist Creation on Ant Media Server**
   - Configure playlist
   - Assign RTMP URL

6. **Save Schedule to Excel**
   - `playlist_schedule_example.xlsx`

## Example Output in `playlist_schedule_example.xlsx`

| Video Name           | Start Time           | Video URL                                          | RTMP URL                          |
|----------------------|----------------------|----------------------------------------------------|------------------------------------|
| video1del11numero1   | 2024-11-01 05:30     | https://yourantmediaserverURL/LiveApp/video1del11numero1.mp4 | rtmp://a.rtmp.youtube.com/live2/generated_key_1 |
| video2del11numero1   | 2024-11-01 07:30     | https://yourantmediaserverURL/LiveApp/video2del11numero1.mp4 | rtmp://a.rtmp.youtube.com/live2/generated_key_2 |
| ...                  | ...                  | ...                                                | ...                                |

## Notes

- **Authentication Required**: Ensure you have sufficient permissions on your YouTube account to create live events and upload thumbnails.
- **Date Modification**: The script is designed to work with the month and day based on the video name. For other cases, make sure the names follow the specified format.

With this workflow, you can automate the scheduling of events on YouTube and playlists on Ant Media Server, customizing the titles, schedules, and thumbnails of each video as needed.

