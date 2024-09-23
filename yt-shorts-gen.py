#!/usr/bin/env python3
import pathlib
import tempfile
from typing import List

import ffmpeg
from PIL import Image
from pydantic import BaseModel


class Quiz(BaseModel):
    question: str = 'The question'
    options: List[str] = ["option 1"]
    answer: str = 'The answer'


class YTShorts:
    def __init__(self, quiz: Quiz, duration=15, background_music='./background.mp3',
                 background_image='pexels-abdghat-1631677.jpg'):
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        self.resized_image = self.tmp_dir.joinpath("resized_image.jpg")
        self.output_video = self.tmp_dir.joinpath("output_video.mp4")
        self.duration = duration
        self.background_image = background_image
        self.background_music = background_music
        self.quiz = quiz

    def resize_picture(self):
        print("resize_picture", self.resized_image)
        img = Image.open(self.background_image)
        img = img.resize((1080, 1920))
        img.save(self.resized_image)

    def mk_video_stream(self):
        print("mk_video_stream")
        video = ffmpeg.input(self.resized_image, loop=1, t=self.duration).filter('scale', 1080, 1920)

        # add question
        video = video.filter(
            'drawtext',
            text=self.quiz.question,
            fontcolor="white",
            fontsize=50,
            x='(w-text_w)/2', y='(h-text_h)/4',
            enable=f'between(t,1,5)'
        )

        # add options
        for option in self.quiz.options:
            video = video.filter(
                'drawtext',
                text=option,
                fontcolor="yellow",
                fontsize=50,
                x='(w-text_w)/2', y='(h-text_h)/4',
                enable=f'between(t,5,10)'
            )

        # add answer
        video = video.filter(
            'drawtext',
            text=self.quiz.answer,
            fontcolor="red",
            fontsize=50,
            x='(w-text_w)/2', y='3*(h-text_h)/4',
            enable=f'between(t,10,15)'
        )

        return video

    def mk_audio_stream(self):
        print("mk_audio_stream")
        audio_stream = ffmpeg.input(self.background_music)
        audio_stream = audio_stream.filter('volume', 0.5)
        audio_stream = audio_stream.filter('atrim', start=0, end=self.duration)
        audio_stream = audio_stream.filter('afade', type='out', start_time=self.duration - 2, duration=2)

        return audio_stream

    def create_shorts_video(self):
        print("create_shorts_video")
        self.resize_picture()
        video_stream = self.mk_video_stream()
        audio_stream = self.mk_audio_stream()

        print("self.output_video", self.output_video)

        ffmpeg.output(
            video_stream, audio_stream, filename=self.output_video,
            vcodec='libx264',
            acodec='aac',
            strict='experimental',
            pix_fmt='yuv420p'
        ).run()


# Example usage of the function
if __name__ == "__main__":
    yts = YTShorts(quiz=Quiz())
    yts.create_shorts_video()

    print(f"Video created at {yts.output_video}")
