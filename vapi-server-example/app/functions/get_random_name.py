import json
import random
import urllib.parse
import urllib.request

nats = [
    "AU",
    "CA",
    "FR",
    "IN",
    "IR",
    "MX",
    "NL",
    "NO",
    "NZ",
    "RS",
    "TR",
    "US",
]


class NameParams:
    def __init__(self, gender=None, nat=None):
        self.gender = gender
        self.nat = nat


def get_random_name(params: NameParams):
    nat = params.nat.upper() if params.nat and params.nat.upper() in nats else random.choice(nats)
    query_params = {
        **{k: v for k, v in params.__dict__.items() if v is not None},
        "nat": nat,
    }
    query_string = urllib.parse.urlencode(query_params)

    try:
        with urllib.request.urlopen(f"https://randomuser.me/api/?{query_string}",
                                    timeout=10) as response:
            data = json.loads(response.read().decode())
        name = data["results"][0]["name"]
        return {
            "result": name["first"] + " " + name["last"],
        }
    except (OSError, ValueError, KeyError, IndexError) as err:
        raise Exception("Error fetching random name") from err
