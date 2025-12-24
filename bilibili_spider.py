import requests
import time
import re

def validate_bvid(bvid):
    if not bvid:
        return False
    # 严格匹配 B 站 BV 号格式：BV + 10位字母数字
    pattern = r'^BV[a-zA-Z0-9]{10}$'
    if re.match(pattern, bvid):
        return True
    return False

def bv_to_aid(bvid):
    if not validate_bvid(bvid):
        print(f"⚠️ 拦截到非法输入或格式错误: {bvid}")
        return None

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        return res['data']['aid'] if res['code'] == 0 else None
    except Exception as e:
        print(f"ID转换失败: {e}")
        return None

def fetch_video_detail(bvid, cookie):
    if not validate_bvid(bvid):
        return None

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": cookie
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        res_json = response.json()
        if res_json.get('code') == 0:
            data = res_json['data']
            return {
                "aid": data.get('aid'),
                "bvid": bvid,
                "title": data.get('title'),
                "pic": data.get('pic'),           # 封面图URL
                "desc": data.get('desc'),         # 简介
                "owner_name": data.get('owner', {}).get('name'), # UP主名字
                "owner_face": data.get('owner', {}).get('face'), # UP主头像
                "view": data.get('stat', {}).get('view'),       # 播放量
                "like": data.get('stat', {}).get('like'),       # 点赞数
                "danmaku": data.get('stat', {}).get('danmaku')  # 弹幕数
            }
    except Exception as e:
        print(f"获取视频详情失败: {e}")
    return None


def is_useless_comment(content):
    clean_text = re.sub(r'@[^ ]+|\[[^\]]+\]', '', content).strip()
    return len(clean_text) < 2


def fetch_bilibili_comments(bvid, cookie, pages=5):
    aid = bv_to_aid(bvid)
    if not aid:
        return [], None

    all_flatten_data = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": cookie,
        "Referer": f"https://www.bilibili.com/video/{bvid}"
    }

    for page in range(1, pages + 1):
        url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&pn={page}&mode=3"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            res_json = response.json()

            if res_json.get('code') == 0 and res_json.get('data', {}).get('replies'):
                replies = res_json['data']['replies']

                for r in replies:
                    # --- 1. 处理主评论 ---
                    main_content = r.get('content', {}).get('message', '')
                    main_rpid = r.get('rpid')

                    # 只有内容有效才进行后续处理
                    if not is_useless_comment(main_content):
                        all_flatten_data.append({
                            'rpid': main_rpid,
                            'content': main_content,
                            'uname': r.get('member', {}).get('uname', '未知用户'),
                            'parent_id': None
                        })

                    # --- 2. 处理嵌套子评论 ---
                    sub_replies = r.get('replies')
                    if sub_replies and isinstance(sub_replies, list):
                        for sub in sub_replies:
                            sub_content = sub.get('content', {}).get('message', '')

                            # 子评论清洗，且关联到当前主评论 ID
                            if not is_useless_comment(sub_content):
                                all_flatten_data.append({
                                    'rpid': sub.get('rpid'),
                                    'content': sub_content,
                                    'uname': sub.get('member', {}).get('uname', '未知用户'),
                                    'parent_id': main_rpid
                                })

                print(f"✅ 第 {page} 页清洗完成，有效数据: {len(all_flatten_data)} 条")
                time.sleep(1.2)
            else:
                break

        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            break

    return all_flatten_data, aid