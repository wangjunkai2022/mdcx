import json
import time


def main(number, appoint_url="", language="zh_cn"):
    start_time = time.time()
    website_name = "local"
    path = "{}_mdcx.json".format(website_name)
    try:
        with open(path, "r") as data_file:
            dic = json.load(data_file)
    except Exception as e:
        debug_info = str(e)
        dic = {
            "title": "",
            "cover": "",
            "website": "",
            "error_info": debug_info,
        }

    dic = {website_name: {"zh_cn": dic, "zh_tw": dic, "jp": dic}}
    js = json.dumps(
        dic,
        ensure_ascii=False,
        sort_keys=False,
        indent=4,
        separators=(",", ": "),
    )  # .encode('UTF-8')

    return js


if __name__ == "__main__":
    main("aaaa", "uhjjjjj")