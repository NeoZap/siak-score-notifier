import httpx

from utils.storage import JSONFileStorage
from utils.logger import log


class DiscordWebhookSender:
    def __init__(
        self,
        data: dict,
        storage: JSONFileStorage,
        discord_webhook: str,
        discord_uid: str,
    ):
        self.data = data
        self.storage = storage
        self.discord_webhook = discord_webhook
        self.discord_uid = discord_uid

    def _build_field(self, course: str, scores: dict) -> dict:
        field = {"name": f"{course}:\n", "value": ""}
        if not scores:
            field["value"] += "- No score table found :(\n"
            return field

        total_score = 0
        for component, component_info in scores.items():
            if component_info["score"] != "Not published":
                score_value = float(component_info["score"])
                percentage_value = float(component_info["percentage"].strip("%")) / 100
                score_contribution = score_value * percentage_value
                field[
                    "value"
                ] += f"- {component}: {component_info['score']} ({component_info['percentage']})\n"
                total_score += score_contribution
            else:
                field["value"] += f"- {component}: Not published\n"

        field["value"] += f"- Total Score: **{total_score}**\n"
        return field

    def _build_message(self) -> list[dict]:
        fields = []
        for i, (course, scores) in enumerate(self.data.items()):
            fields.append(self._build_field(f"{i+1}. {course}", scores))
        return fields

    def _send_webhook(self, content: str, embeds: list[dict]) -> None:
        httpx.post(self.discord_webhook, json={"content": content, "embeds": embeds})

    def send(self):
        is_modified = self.storage.load() != self.data

        if not is_modified:
            log.info("No score modification found.")
            self._send_webhook(
                "Just a healthcheck",
                [{"title": "SIAK Score Update", "description": "No new changes yet."}],
            )
            log.success("Healthcheck sent!")
        else:
            fields = self._build_message()
            log.info("Score modification found:")
            for field in fields:
                course, details = field["name"], field["value"]
                print(f"{course}")
                print(f"{details}")
            self.storage.dump(self.data)
            self._send_webhook(
                f"<@{self.discord_uid}>",
                [
                    {
                        "title": "SIAK Score Update",
                        "description": "New score changes!",
                        "fields": fields,
                    }
                ],
            )
            log.success("Score modification sent!")
