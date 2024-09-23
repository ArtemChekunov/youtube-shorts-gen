#!/usr/bin/env python3
import json
import pathlib
import random
import tempfile
from typing import List

import ffmpeg
from PIL import Image
from openai import OpenAI
from pydantic import BaseModel


class Quiz(BaseModel):
    question: str
    options: List[str]
    answer: str


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
            enable=f'between(t,0,5)'
        )

        # add options
        video = video.filter(
            'drawtext',
            text="Options:",
            fontcolor="yellow",
            fontsize=50,
            x='(w-text_w)/2', y='(h-text_h)/4',
            enable=f'between(t,5,10)'
        )

        shift = 70
        random.shuffle(self.quiz.options)
        for ix, option in enumerate(self.quiz.options):
            video = video.filter(
                'drawtext',
                text=f"{ix + 1}) {option}",
                fontcolor="white",
                fontsize=50,
                x=f'450', y=f'((h-text_h)/4)+{shift}',
                enable=f'between(t,5,10)'
            )
            shift = shift + 60

        # add answer
        video = video.filter(
            'drawtext',
            text=self.quiz.answer,
            fontcolor="white",
            fontsize=50,
            x='(w-text_w)/2', y='(h-text_h)/4',
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


def get_quizzes(theme: str, size: int = 3):
    client = OpenAI()
    prompt = f"""
        Please provide a list of {size} quizzes about {theme} in **valid JSON format**. 
        The JSON should be an array of dictionaries. 
        Each dictionary must have the following fields:
        
        - "question" (string): The quiz question.
        - "options" (array of strings): The available options.
        - "answer" (string): The correct answer.
        
        **Important**: 
        - Return only the raw JSON content.
        - Do not include any additional labels, such as `content` or `json_string`.
        - Do not include any explanations, comments, or text before or after the JSON.
        - Ensure that the response is valid, properly formatted JSON.
        - If there are no results, return an empty array (`[]`).
    """

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": prompt
            },
        ],
        temperature=0.7,
        max_tokens=3500
    )

    content = completion.choices[0].message.content

    try:
        return json.loads(content)

    except:
        print("content", content)
        raise


def main():
    # quizzes = get_quizzes(theme="capital cities", size=3)
    quizzes = [
        {'question': 'What is the capital city of France?', 'options': ['Paris', 'Berlin', 'Madrid', 'Rome'],
         'answer': 'Paris'},
        {'question': 'What is the capital city of Japan?', 'options': ['Tokyo', 'Beijing', 'Seoul', 'Bangkok'],
         'answer': 'Tokyo'},
        {'question': 'What is the capital city of Australia?',
         'options': ['Sydney', 'Melbourne', 'Canberra', 'Perth'], 'answer': 'Canberra'}
    ]
    result = []
    for i in quizzes:
        print("quiz", i)
        yts = YTShorts(quiz=Quiz(**i))
        yts.create_shorts_video()
        result.append(yts)

    print(quizzes)

    for yts in result:
        print(f"Video created at {yts.output_video}")


if __name__ == "__main__":
    # yts = YTShorts(quiz=Quiz(
    #     question='The question',
    #     options=["option 1", "option 2", "option 3"],
    #     answer="The answer"
    # ))
    # yts.create_shorts_video()
    # print(f"Video created at {yts.output_video}")
    main()
