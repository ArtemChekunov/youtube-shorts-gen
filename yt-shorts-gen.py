#!/usr/bin/env python3
import argparse
import json
import pathlib
import random
import sys
import tempfile
from functools import cached_property
from typing import List, Optional, Dict

import ffmpeg
import yaml
from PIL import Image
from openai import OpenAI
from pydantic import BaseModel


class MyBaseModel(BaseModel):
    background_music: str = './assets/music/default_background.mp3'
    background_image: str = './assets/pictures/default_background.jpg'


class Quiz(MyBaseModel):
    question: str
    options: List[str]
    answer: str

class Storage:
    def __init__(self, name):
        self.path = pathlib.Path("profiles.d").joinpath(f"{name}.yaml")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    @property
    def data(self):
        with self.path.open() as f:
            data = yaml.safe_load(f.read())
            return data if data else []

    def write(self, data):
        with self.path.open('w') as f:
            return f.write(yaml.dump(data))


class Profile(MyBaseModel):
    name: str
    static: Optional[List[Dict]] = None
    prompt_theme: Optional[str] = None
    prompt_request_size: int = 3

    @property
    def storage(self):
        return Storage(self.name)

    @cached_property
    def quizzes(self) -> List[Quiz]:
        if self.static:
            result = self.static

        elif self.prompt_theme:
            result = get_quizzes(theme=self.prompt_theme, size=self.prompt_request_size, exclude=self.storage.data)
        else:
            raise Exception("static or prompt_theme should be defined")

        defaults = {"background_music": self.background_music, "background_image": self.background_image}
        return [Quiz(**{**defaults, **i}) for i in result]

    def save_quizzes(self):
        data = self.storage.data


        for i in self.quizzes:
            data.append(i.question)

        self.storage.write(list(set(data)))

class Config(BaseModel):
    profiles: Dict[str, Profile]


class YTShorts:
    def __init__(self, quiz: Quiz):
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        self.resized_image = self.tmp_dir.joinpath("resized_image.jpg")
        self.output_video = self.tmp_dir.joinpath("output_video.mp4")
        self.duration = 15
        self.quiz = quiz

    def resize_picture(self):
        print("resize_picture", self.resized_image)
        img = Image.open(self.quiz.background_image)
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
        audio_stream = ffmpeg.input(self.quiz.background_music)
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


def get_quizzes(theme: str, size: int = 3, exclude=lambda: []):
    client = OpenAI()
    prompt = f"""
        Please provide a list of {size} quizzes about {theme} but exclude question names {exclude} in **valid JSON format**. 
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


def main(args):
    with pathlib.Path("profiles.yaml").open() as f:
        config = Config(**yaml.safe_load(f.read()))

    try:
        profile = config.profiles[args.profile]
    except KeyError:
        print(f"Profile {args.profile} doesn't exist")
        sys.exit(1)

    print("profile", profile.quizzes)
    result = []
    for i in profile.quizzes:
        print("quiz", i)
        yts = YTShorts(quiz=i)
        yts.create_shorts_video()
        result.append(yts)

    print(profile.quizzes)

    profile.save_quizzes()
    for yts in result:
        print(f"Video created at {yts.output_video}")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True, help='profile name')
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    main(args)
