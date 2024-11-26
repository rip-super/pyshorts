import requests
import time
from gtts import gTTS
import threading
import subprocess
import random
import os
from datetime import datetime

date = datetime.today().strftime('%m-%d-%Y')

def generate_facts(output_folder):
    # API URL and key for fetching random facts from api-ninjas
    api_url = "https://api.api-ninjas.com/v1/facts"
    api_key = "YOUR API KEY"
    all_facts = open(r"assets\all_facts.txt", "r").read().split("\n")
    curr_facts = []

    def get_fact():
        while True:
            # Send a GET request to the API to fetch a random fact
            response = requests.get(api_url, headers={"X-Api-Key": api_key})
            
            # Check if the response was successful
            if response.status_code == requests.codes.ok:
                # Parse the JSON response to extract the fact
                data = response.json()
                # Clean the fact string by removing quotes, commas, and periods
                fact = data[0]["fact"].strip("\"").replace(",", "").replace(".", "")
                
                # Only save facts with 125 characters or less that have not already been used
                if len(fact) <= 100 and str(fact) not in all_facts and str(fact) not in curr_facts:
                    # Append the fact to the 'facts.txt' file in the specified output folder
                    with open(os.path.join(output_folder, "facts.txt"), "a") as f:
                        f.write(fact + "\n")
                        curr_facts.append(str(fact))
                    # Also append the fact to the 'all_facts.txt' file
                    with open(r"assets\all_facts.txt", "a") as f:
                        f.write(fact + "\n")
                    break
            else:
                # Print an error message if the API request fails
                print("Error:", response.status_code, response.text)

    # Create a list of threads to fetch multiple facts concurrently
    threads = [threading.Thread(target=get_fact) for _ in range(8)]
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Print a success message once all facts have been generated
    print("Facts successfully generated")

def text_to_speech(filename, output_folder):
    try:
        # Open the 'facts.txt' file in the specified output folder and read the facts
        with open(os.path.join(output_folder, "facts.txt"), "r") as f:
            # Read all facts, strip leading/trailing whitespace, and split by new line
            facts = f.read().strip().split("\n")[:8]
        
        # Combine the first 7 facts into a single string, separated by " , "
        combined_facts = " , ".join(facts)
        
        # Use gTTS (Google Text-to-Speech) to convert the combined facts to speech
        tts = gTTS(text=combined_facts, lang='en')
        
        # Save the generated speech as an MP3 file in the specified output folder
        tts.save(os.path.join(output_folder, filename))
        
        # Print a success message indicating where the MP3 file was saved
        print(f"gTTS saved to {filename}")
    
    except Exception as e:
        # Print an error message if an exception occurs during text-to-speech processing
        print("Error with gTTS:", e)

def mp3_to_srt(mp3_file, srt_file):
    # API key and endpoints for AssemblyAI
    API_KEY = 'YOUR API KEY'
    UPLOAD_URL = 'https://api.assemblyai.com/v2/upload'
    TRANSCRIBE_URL = 'https://api.assemblyai.com/v2/transcript'
    CHECK_STATUS_URL = 'https://api.assemblyai.com/v2/transcript/{}'

    # Headers for making requests to AssemblyAI
    headers = {
        'authorization': API_KEY,
        'content-type': 'application/json'
    }

    def upload_file(file_path):
        """Upload the MP3 file to AssemblyAI and return the audio URL."""
        with open(file_path, 'rb') as f:
            response = requests.post(UPLOAD_URL, headers={'authorization': API_KEY}, files={'file': f})
            response.raise_for_status()  # Raise an error if the request fails
            return response.json()['upload_url']  # Extract and return the upload URL

    def start_transcription(audio_url):
        """Initiate transcription for the uploaded audio file and return the transcript ID."""
        response = requests.post(TRANSCRIBE_URL, headers=headers, json={'audio_url': audio_url})
        response.raise_for_status()  # Raise an error if the request fails
        return response.json()['id']  # Extract and return the transcript ID

    def check_transcription_status(transcript_id):
        """Check the status of the transcription job using the transcript ID."""
        response = requests.get(CHECK_STATUS_URL.format(transcript_id), headers=headers)
        response.raise_for_status()  # Raise an error if the request fails
        return response.json()  # Return the transcription status and details

    def generate_srt(transcript, srt_file):
        """Generate an SRT file from the transcription data provided by AssemblyAI."""
        words = transcript.get('words', [])  # Extract the word-level timestamps from the transcript
        subtitles = []

        # Loop through the words to create SRT-formatted subtitles
        for i, word in enumerate(words):
            start_time = word['start'] / 1000  # Convert start time to seconds
            end_time = word['end'] / 1000  # Convert end time to seconds
            text = word['text']  # Extract the word text

            # Format the start and end times to SRT time format (HH:MM:SS,ms)
            start = time.strftime('%H:%M:%S', time.gmtime(start_time)) + ',' + str(int(start_time * 1000 % 1000)).zfill(3)
            end = time.strftime('%H:%M:%S', time.gmtime(end_time)) + ',' + str(int(end_time * 1000 % 1000)).zfill(3)
            
            # Append the subtitle in SRT format
            subtitles.append(f"{i + 1}\n{start} --> {end}\n{text}\n")

        # Write the generated subtitles to the SRT file
        with open(srt_file, 'w') as f:
            f.writelines(subtitles)
        print(f"Subtitles saved to {srt_file}")

    """Convert an MP3 file to an SRT file using AssemblyAI."""
    try:
        # Upload the MP3 file and get the audio URL
        audio_url = upload_file(mp3_file)
        
        # Start the transcription process and get the transcript ID
        transcript_id = start_transcription(audio_url)

        # Poll the transcription status until it's completed or failed
        while True:
            transcript = check_transcription_status(transcript_id)
            if transcript['status'] == 'completed':
                # If transcription is complete, generate the SRT file
                generate_srt(transcript, srt_file)
                break
            elif transcript['status'] == 'failed':
                # Handle failed transcription
                print('Transcription failed.')
                break
            else:
                # If transcription is still in progress, wait and check again
                print('Transcription in progress...')
                time.sleep(10)

    except Exception as e:
        # Catch any exceptions during the process and print an error message
        print("Error with transcription or SRT generation:", e)

def get_duration(file_path):
    """Get the duration of a media file in seconds using ffprobe."""
    try:
        # Run the ffprobe command to extract the duration of the file
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        # Strip any leading/trailing whitespace from the result to get the duration
        duration = result.stdout.strip()
        
        # Check if the duration is empty and raise an error if it is
        if not duration:
            raise ValueError(f"Could not get duration for {file_path}. Output was empty.")
        
        # Return the duration as a float
        return float(duration)
    
    except subprocess.CalledProcessError as e:
        # Handle errors from the subprocess call to ffprobe
        raise RuntimeError(f"Error with ffprobe: {e.stderr}")
    
    except ValueError as e:
        # Handle errors in parsing the duration value
        raise ValueError(f"Error parsing duration: {e}")

def extract_video_clip(video_file, audio_file, output_file, output_folder):
    """Extract a video clip from `video_file` matching the length of `audio_file`.
    
    The clip will be of `clip_length` seconds, randomly selected from the `video_file`.
    The extracted clip will be saved in the specified `output_folder` with the name `output_file`.
    """
    
    # Get the duration of the audio file (clip length) and video file
    clip_length = get_duration(os.path.join(output_folder, audio_file))
    video_duration = get_duration(video_file)

    # Raise an error if the clip length is longer than the video duration
    if clip_length > video_duration:
        raise ValueError("Clip length is longer than the video duration.")
    
    # Calculate a random start time for the clip within the video duration
    start_time = random.uniform(0, video_duration - clip_length)
    
    # Construct the ffmpeg command to extract the video clip
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', str(start_time), '-i', video_file, '-t', str(clip_length),
        '-an', '-c:v', 'copy', '-vsync', '1', os.path.join(output_folder, output_file)
    ]
    
    # Run the ffmpeg command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Check for errors during the ffmpeg process
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr)

    # Print success message with details of the extracted clip
    print(f"Extracted {clip_length} seconds of video from {video_file} starting at {start_time} seconds and saved to {output_file}")

def extract_audio_clip(audio_file, mp3_file, output_file, output_folder):
    """Extract an audio clip from `audio_file` matching the length of `mp3_file` and save it as an MP3.

    The clip will be of `clip_length` seconds, randomly selected from the `audio_file`.
    The extracted clip will be saved in the specified `output_folder` with the name `output_file`.
    """

    # Get the duration of the MP3 file (clip length) and the original audio file
    clip_length = get_duration(os.path.join(output_folder, mp3_file))
    audio_duration = get_duration(audio_file)

    # Raise an error if the clip length is longer than the audio duration
    if clip_length > audio_duration:
        raise ValueError("Clip length is longer than the audio duration.")
    
    # Calculate a random start time for the clip within the audio duration
    start_time = random.uniform(0, audio_duration - clip_length)
    
    # Construct the ffmpeg command to extract the audio clip and encode it as MP3
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', audio_file, '-ss', str(start_time), '-t', str(clip_length),
        '-c:a', 'libmp3lame', os.path.join(output_folder, output_file)  # Use libmp3lame for MP3 encoding
    ]
    
    # Run the ffmpeg command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Check for errors during the ffmpeg process
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr)

    # Print success message with details of the extracted clip
    print(f"Extracted {clip_length} seconds of audio from {audio_file} starting at {start_time} seconds and saved to {output_file}")

def combine_video_audio_subtitles(video_file, audio_file1, audio_file2, subtitle_file, output_file, output_folder):
    """Combine video, audio (with reduced volume), and subtitles into a single MP4 file.

    This function takes a video file, two audio files, and a subtitle file, 
    and combines them into a single MP4 video. The first audio stream remains at its original volume,
    while the second audio stream's volume is reduced to 50%. The subtitles are overlaid on the video.
    """

    # Correctly format the file paths for FFmpeg, replacing backslashes with forward slashes
    video_path = os.path.join(output_folder, video_file).replace("\\", "/")
    audio_path_1 = os.path.join(output_folder, audio_file1).replace("\\", "/")
    audio_path_2 = os.path.join(output_folder, audio_file2).replace("\\", "/")
    subtitle_path = os.path.join(output_folder, subtitle_file).replace("\\", "/")
    output_path = os.path.join(output_folder, output_file).replace("\\", "/")

    # Construct the FFmpeg command to combine video, audio, and subtitles
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', video_path,
        '-i', audio_path_1, '-i', audio_path_2,
        '-filter_complex', (
            f"[1:a]volume=1[a1];"  # Keep volume of the first audio stream unchanged
            f"[2:a]volume=0.50[a2];"  # Set volume of the second audio stream (music_clip) to 0.50 (50% volume)
            f"[a1][a2]amix=inputs=2[a];"  # Mix the adjusted audio streams
            f"[0:v]subtitles={subtitle_path}:force_style='Alignment=10,"
            f"FontFile=assets/Poppins-Regular.ttf'[v]"  # Use Poppins Regular font and align subtitles
        ),
        '-map', '[v]', '-map', '[a]',  # Map the video and mixed audio streams to the output
        '-c:v', 'libx264', '-vsync', '1',  # Use H.264 codec for video and adjust video synchronization
        '-c:a', 'aac', '-r', '60',  # Use AAC codec for audio and set frame rate to 60fps
        '-metadata', f'title=Your Daily Dose of Facts {date} | #shorts #facts #funfacts #daily #dailyfacts #original',
        '-metadata', 'artist=Daily Dose of Facts',  # Set metadata for title and artist
        output_path
    ]

    # Execute the FFmpeg command and check for errors
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error (video processing):", result.stderr)
    else:
        print(f"Video saved to {output_file}")

def convert_to_yt_short(input_file, output_folder):
    """Convert a video to YouTube Shorts format (1080x1920, 9:16 aspect ratio, max 60 seconds).

    This function takes a video file and converts it to the YouTube Shorts format, which requires a 9:16 aspect ratio,
    a resolution of 1080x1920 pixels, and a maximum duration of 60 seconds. The output video is saved in the specified 
    output folder with the name 'yt_short.mp4'.
    """
    
    # Define the output file path and ensure proper formatting
    output_file = os.path.join(output_folder, 'yt_short.mp4').replace("\\", "/")
    
    # Construct the FFmpeg command to crop and resize the video
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', input_file,
        '-vf', 'crop=ih*(9/16):ih,scale=1080:1920',  # Crop to 9:16 aspect ratio and resize to 1080x1920
        '-t', '60',  # Limit video duration to 60 seconds
        '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '192k',  # Use H.264 for video encoding and AAC for audio encoding
        '-preset', 'fast', '-crf', '23',  # Use a fast encoding preset with a CRF value of 23 for good quality
        output_file
    ]
    
    # Execute the FFmpeg command and capture the output
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Check for errors and print appropriate message
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}")
    else:
        print(f"Video converted to YouTube Shorts format and saved to {output_file}")

def main():
    print("Please verify you have a stable internet connection")
    os.system("pause")
    os.makedirs("output", exist_ok=True)
    generate_facts("output")
    text_to_speech("facts.mp3", "output")
    mp3_to_srt("output/facts.mp3", "output/transcript.srt")
    extract_video_clip("assets/minecraft_parkour.webm", "facts.mp3", "minecraft_clip.mp4", "output")
    extract_audio_clip("assets/music.m4a", "facts.mp3", "music_clip.mp3", "output")
    combine_video_audio_subtitles("minecraft_clip.mp4","facts.mp3", "music_clip.mp3", "transcript.srt", "video.mp4", "output")
    convert_to_yt_short("output/video.mp4", "output")

if __name__ == "__main__":
    main()
