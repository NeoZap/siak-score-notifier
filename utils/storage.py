import json


class JSONFileStorage:
    def __init__(self, filename: str):
        self.filename = filename

    def load(self) -> dict[str, dict]:
        try:
            with open(self.filename, "r") as fd:
                return json.load(fd)
        except FileNotFoundError:
            return {}

    def dump(self, content: dict[str, dict]):
        with open(self.filename, "w") as fd:
            json.dump(content, fd)
