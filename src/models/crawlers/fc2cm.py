import json
import time
from models.base.web import get_html
from models.config.config import config
from lxml import etree


def getTitle(html):  # 获取标题
    result = html.xpath('//h1[@class="entry-title"]//a/text()')
    if result:
        result = " ".join(result)
    else:
        result = ""
    return result


def getStudio(html):
    result = html.xpath('//a[@rel="category"]/text()')
    if result:
        result = " ".join(result)
    else:
        result = ""
    return result


def getRelease(html):
    result = html.xpath('//div[@class="single_art"]/table/tr[3]/td[3]/p/text()')
    if result:
        result = " ".join(result)
    else:
        result = ""
    return result


def getOutline(html):
    result = html.xpath('//div[@class="single_art"]/p/text()')
    if result:
        result = " ".join(result)
    else:
        result = ""
    return result


def getTag(html):
    result = html.xpath('//div[@class="single_art"]/table/tr[6]/td[3]//a/text()')
    if result:
        result = ",".join(result)
    else:
        result = ""
    return result


def getMosaic(tag, title):  # 获取马赛克
    if "無修正" in tag or "無修正" in title:
        result = "无码"
    else:
        result = "有码"
    return result


def main(number, appoint_url="", language="jp"):
    number = (
        number.upper()
        .replace("FC2PPV", "")
        .replace("FC2-PPV-", "")
        .replace("FC2-", "")
        .replace("-", "")
        .strip()
    )
    start_time = time.time()
    website_name = "fc2cm"
    real_url = appoint_url
    dic = {}
    web_info = "\n       "
    debug_info = ""
    try:  # 捕获主动抛出的异常
        if not real_url:
            real_url = "https://fc2cm.com/?p=" + number

        debug_info = "番号地址: %s" % real_url

        # ========================================================================番号详情页
        result, html_content = get_html(real_url)
        if not result:
            debug_info = "网络请求错误: %s" % html_content
            raise Exception(debug_info)
        html_info = etree.fromstring(html_content, etree.HTMLParser())

        title = getTitle(html_info)  # 获取标题
        if "" == title:
            debug_info = "搜索结果: 未匹配到番号！"
            raise Exception(debug_info)

        # poster_url = getCoverSmall(html_info)
        outline = getOutline(html_info)
        tag = getTag(html_info)
        release = getRelease(html_info)
        studio = getStudio(html_info)  # 使用卖家作为厂商
        if "fc2_seller" in config.fields_rule:
            actor = studio
        else:
            actor = ""

        # mosaic = getMosaic(tag, title)
        mosaic = ""
        try:
            dic = {
                "number": "FC2-PPV-" + str(number),
                "title": title,
                "originaltitle": title,
                "actor": actor,
                "outline": outline,
                "originalplot": outline,
                "tag": tag,
                "release": release,
                "year": release[:4],
                "runtime": "",
                "score": "",
                "series": "FC2系列",
                "director": "",
                "studio": studio,
                "publisher": studio,
                "source": "fc2",
                "website": real_url,
                "cover": "",
                "poster": "",
                "extrafanart": "",
                "trailer": "",
                "image_download": "",
                "actor_photo": {actor: ""},
                "image_cut": "",
                "error_info": "",
                "mosaic": mosaic,
                "wanted": "",
            }
            debug_info = "数据获取成功！"
        except Exception as e:
            debug_info = "数据生成出错: %s" % str(e)
            raise Exception(debug_info)

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
    )
    return js


if __name__ == "__main__":
    # yapf: disable
    print(main('fc2-4669744',
               ''))  
