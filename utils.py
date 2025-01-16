import re


def msg(msg, version="2.0"):
    return {
        "version": version,
        "data": {
            "msg": msg
        }
    }


def extract_json_str(text):
    pattern = r'```json\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)  # re.DOTALL은 개행문자도 매칭되게 함
    if match:
        return match.group(1).strip()
    return None
