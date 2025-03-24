import json
import time


def main(number, appoint_url="", log_info="", req_web="", language="zh_cn"):
    start_time = time.time()
    website_name = "local_file"
    log_info += "\n     搜刮的Number:{}".format(number)
    log_info += "\n     搜刮的Url:{}".format(appoint_url)
    log_info += "\n     尝试加载本地json数据"
    path = "{}_mdcx.json".format(website_name)
    log_info += "\n     本地json文件路径 {}".format(path)
    try:
        with open(path, "r") as data_file:
            dic = json.load(data_file)
        dic["log_info"] = log_info
    except Exception as e:
        debug_info = str(e)
        dic = {
            "title": "",
            "cover": "",
            "website": "",
            "log_info": log_info,
            "error_info": debug_info,
            "req_web": req_web
            + "(%ss) "
            % (
                round(
                    (time.time() - start_time),
                )
            ),
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
