#!/usr/bin/env python3
import ffmpeg
from PIL import Image
import tempfile
import pathlib

# Function to create a video from an image with text at different timeslots
def create_shorts_video(image_path, output_path, texts, duration=15):
    # Ensure the image is vertical (1080x1920)
    img = Image.open(image_path)
    img = img.resize((1080, 1920))

    temp_dir = tempfile.TemporaryDirectory()

    resized_image_path = pathlib.Path(temp_dir.name).joinpath("resized_image.jpg")
    img.save(resized_image_path)

    # Prepare the ffmpeg command using the ffmpeg-python library
    video = (
        ffmpeg
        .input(resized_image_path, loop=1, t=duration)  # Loop image to match video duration
        .filter('scale', 1080, 1920)  # Set scale to 1080x1920
    )

    # Add different texts at different times using the drawtext filter
    for idx, (text, start, end, color, position) in enumerate(texts):
        x, y = position
        video = video.filter(
            'drawtext',
            text=text,
            fontcolor=color,
            fontsize=50,
            x=x,
            y=y,
            enable=f'between(t,{start},{end})'
        )

    audio_stream = ffmpeg.input('./background.mp3')
    audio_stream = audio_stream.filter('volume', 0.5)
    audio_stream = audio_stream.filter('atrim', start=0, end=duration)
    audio_stream = audio_stream.filter('afade', type='out', start_time=duration - 2, duration=2)

    ffmpeg.output(video, audio_stream, output_path, vcodec='libx264', acodec='aac', strict='experimental', pix_fmt='yuv420p').run()


# Example usage of the function
if __name__ == "__main__":
    # Image path
    image_path = 'pexels-abdghat-1631677.jpg'

    # Text overlays with times and colors
    # (text, start_time, end_time, color, (x_position, y_position))
    texts = [
        ("Welcome", 0, 5, "white", ("(w-text_w)/2", "(h-text_h)/4")),
        ("Enjoy the Content", 5, 10, "yellow", ("(w-text_w)/2", "(h-text_h)/2")),
        ("Thank You!", 10, 15, "red", ("(w-text_w)/2", "3*(h-text_h)/4")),
    ]

    # Output video path
    output_path = 'output_video.mp4'

    # Create the video with the image and texts
    create_shorts_video(image_path, output_path, texts)

    print(f"Video created at {output_path}")
