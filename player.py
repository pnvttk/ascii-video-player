import cv2
import numpy as np
import curses
from yt_dlp import YoutubeDL
import sys
import argparse
import os
import subprocess
import pygame
import threading
import time
import signal

# Global variables to store filenames for cleanup
video_file = None
audio_file = None

def signal_handler(sig, frame):
    print("\nInterrupt received, cleaning up...")
    cleanup()
    sys.exit(0)

def cleanup():
    global video_file, audio_file
    pygame.mixer.quit()
    if video_file and os.path.exists(video_file):
        os.remove(video_file)
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)

    print("Cleanup complete. Exiting.")

def download_video(url):
    global video_file
    ydl_opts = {
        'outtmpl': 'video.%(ext)s',
        'format': 'best[ext=mp4]/best'
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_file = ydl.prepare_filename(info)

    return video_file

def extract_audio(video_file):
    global audio_file
    audio_file = "audio.mp3"
    subprocess.call(['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', audio_file, '-y'])

    return audio_file

def play_audio(audio_file):
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()

def frame_to_ascii(frame, width, height):
    frame = cv2.resize(frame, (width, height))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    ascii_chars = ['@', '#', 'S', '%', '?', '*', '+', ';', ':', ',', '.']
    ascii_frame = np.array([ascii_chars[pixel//25] for pixel in frame.flatten()]).reshape(height, width)

    return '\n'.join([''.join(row) for row in ascii_frame])

def play_video(stdscr, filename):
    curses.curs_set(0)
    height, width = stdscr.getmaxyx()
    cap = cv2.VideoCapture(filename)
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        ascii_frame = frame_to_ascii(frame, width-1, height-1)
        stdscr.clear()
        stdscr.addstr(0, 0, ascii_frame)
        stdscr.refresh()
        
        frame_count += 1
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        
        time_to_sleep = (frame_count / cap.get(cv2.CAP_PROP_FPS)) - elapsed_time
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)

    cap.release()

def main():
    parser = argparse.ArgumentParser(description="Play YouTube videos as ASCII art with audio in the terminal.")
    parser.add_argument("url", help="YouTube video URL")
    args = parser.parse_args()

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    try:
        print("Downloading video...")
        video_file = download_video(args.url)
        print(f"Download complete. Saved as: {video_file}")

        print("Extracting audio...")
        audio_file = extract_audio(video_file)
        print("Audio extraction complete.")

        print("Starting playback...")
        audio_thread = threading.Thread(target=play_audio, args=(audio_file,))
        audio_thread.start()

        curses.wrapper(lambda stdscr: play_video(stdscr, video_file))

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up
        cleanup()

if __name__ == "__main__":
    main()