import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from typing import Optional

import requests
import pytz
from eth_account import Account
from eth_account.messages import encode_defunct
from utils.logger import logger


BASE_URL   = "https://task.simplechain.com"
KEYS_FILE  = "keys.txt"
PROXY_FILE = "proxy.txt"

TZ = pytz.timezone("Asia/Shanghai")

DELAY_BETWEEN_WALLETS = 5
DELAY_BETWEEN_TASKS   = 2

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/146.0.0.0 Safari/537.36")

TASK_VISIT   = "ACCESS_LINK"
TASK_CHECKIN = "DAILY_CHECK_IN"
DONE_STATUSES = {"COMPLETED_TODAY", "COMPLETED"}


KNOWN_SCHEMES = ("http://", "https://", "socks4://", "socks5://", "socks5h://", "socks4a://")

def normalize_proxy(raw: str) -> str:
    raw = raw.strip()
    lower = raw.lower()
    if any(lower.startswith(s) for s in KNOWN_SCHEMES):
        return raw
    return "http://" + raw

def load_proxies(path: str) -> list:
    if not os.path.exists(path):
        return []
    proxies = []
    with open(path) as f:
        for line_ in f:
            line_ = line_.strip()
            if line_ and not line_.startswith("#"):
                proxies.append(normalize_proxy(line_))
    return proxies

def make_session(proxy: Optional[str] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": BASE_URL,
        "referer": f"{BASE_URL}/",
        "user-agent": UA,
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
        logger.info(f"使用代理: {s.proxies.get('http', 'none')}")
    return s


def api_get(session, path: str, token: str) -> dict:
    r = session.get(BASE_URL + path,
                    headers={"authorization": f"Bearer {token}"},
                    timeout=15)
    r.raise_for_status()
    return r.json()

def api_post(session, path: str, body: dict, token: Optional[str] = None) -> dict:
    h = {"authorization": f"Bearer {token}"} if token else {}
    r = session.post(BASE_URL + path, json=body, headers=h, timeout=15)
    r.raise_for_status()
    return r.json()


def wallet_login(session, address: str, private_key: str) -> str:
    r = api_post(session, "/api/v1/get/nonce", {"address": address})
    if r.get("code") != 0:
        raise RuntimeError(f"获取 nonce 失败: {r.get('message')}")

    data = r.get("data", {})
    if isinstance(data, dict) and data.get("message"):
        message = data["message"]
    else:
        nonce = data.get("nonce") if isinstance(data, dict) else data
        message = (
            "Welcome to SimpleChain!\n\n"
            "Click to sign in and accept the SimpleChain Terms of Service.\n\n"
            "This request will not trigger a blockchain transaction or cost any gas fees.\n\n"
            f"Nonce: {nonce}"
        )

    raw_sig = Account.from_key(private_key).sign_message(
        encode_defunct(text=message)).signature.hex()
    sig = raw_sig if raw_sig.startswith("0x") else "0x" + raw_sig

    r2 = api_post(session, "/api/v1/login",
                  {"address": address, "message": message, "signature": sig})
    if r2.get("code") != 0:
        raise RuntimeError(f"登录失败: {r2.get('message')}")

    token = r2.get("data", {}).get("token") or r2.get("data", {}).get("accessToken") or ""
    if not token and isinstance(r2.get("data"), str):
        token = r2["data"]
    if not token:
        raise RuntimeError(f"未获取到 token: {r2}")
    return token


def get_tasks(session, token: str) -> list:
    try:
        r = api_get(session, "/api/v1/task/list", token)
        d = r.get("data", {})
        if isinstance(d, dict):
            d = d.get("tasks") or d.get("list") or d.get("items") or []
        return d if isinstance(d, list) else []
    except Exception:
        return []

def do_visit(session, token: str, tasks: list) -> bool:
    task = next((t for t in tasks if t.get("taskCode") == TASK_VISIT), None)
    if not task:
        logger.warning("未找到访问任务")
        return False

    if task.get("completionStatus") in DONE_STATUSES:
        logger.info("<g>✔</g> 访问任务今日已完成")
        return True

    task_id = task.get("taskId") or task.get("id") or ""
    if not task_id:
        logger.error("无法获取任务ID")
        return False

    try:
        r = api_post(session, "/api/v1/task/complete",
                     {"taskId": task_id}, token=token)
        if r.get("code") == 0:
            data = r.get("data", {})
            task_name = data.get("taskName", "访问任务")
            reward = data.get("rewardPoints", "?")
            logger.info(f"任务: {task_name} , 奖励: <y>{reward}</y>")
            return True

        if "already" in str(r.get("message", "")).lower():
            logger.info("访问任务已完成（重复提交）")
            return True

        logger.error(f"访问任务失败: {r.get('message', '未知错误')}")
        return False
    except Exception as e:
        logger.opt(exception=True).error(f"访问任务异常: {e}")
        return False

def do_checkin(session, token: str, tasks: list) -> bool:
    task = next((t for t in tasks if t.get("taskCode") == TASK_CHECKIN), None)
    if task and task.get("completionStatus") in DONE_STATUSES:
        logger.info("✔ 签到已完成")
        return True
    try:
        r = api_post(session, "/api/v1/campaign/checkin", {}, token=token)
        code = r.get("code")
        msg = r.get("message", "")
        if code == 0:
            data = r.get("data", {})
            task_name = data.get("taskName", "签到")
            reward = data.get("totalReward", "?")
            logger.info(f"任务: {task_name} , 奖励: <y>{reward}</y>")
            return True
        if "already" in msg.lower() or "today" in msg.lower() or code in (409, 10001, 10002):
            logger.info("签到已完成（重复提交）")
            return True
        logger.error(f"签到失败: {msg}")
        return False
    except Exception as e:
        logger.opt(exception=True).error(f"签到异常: {e}")
        return False

def get_user_rank_info(session: requests.Session, token: str) -> Optional[dict]:
    try:
        r = api_get(session, "/api/v1/user/rank/change/info", token)
        if r.get("code") != 0:
            logger.warning(f"获取排名信息失败: {r.get('message')}")
            return None
        return r.get("data", {})
    except Exception as e:
        logger.opt(exception=True).error(f"请求排名接口异常: {e}")
        return None

def log_user_stats(session: requests.Session, token: str):
    data = get_user_rank_info(session, token)
    if not data:
        return

    points = data.get("points", {})
    rank = data.get("rank", {})

    points_curr = points.get("current", "?")
    points_change = points.get("changeText", "?")
    rank_curr = rank.get("current", "?")
    rank_change = rank.get("changeText", "?")

    logger.info(
        f"总积分: <y>{points_curr}</y> (<g>{points_change}</g>) | "
        f"排名: <y>{rank_curr}</y> (<g>{rank_change}</g>)"
    )


def run_wallet(private_key: str, proxy: Optional[str],
               index: int, total: int) -> bool:
    private_key = private_key.strip()
    if not private_key or private_key.startswith("#"):
        return False
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    try:
        address = Account.from_key(private_key).address
        short   = address[:6] + "..." + address[-4:]
        logger.info(f"<g>{index}. {short}</g>")

        session = make_session(proxy)

        try:
            token = wallet_login(session, address, private_key)
            logger.info("登录成功...")
        except Exception as e:
            logger.error(f"登录失败，原因：{e}")
            return False

        tasks = get_tasks(session, token)

        # time.sleep(1)
        # do_visit(session, token, tasks)
        # time.sleep(DELAY_BETWEEN_TASKS)
        #
        # do_checkin(session, token, tasks)
        # time.sleep(2)
        # log_user_stats(session, token)
        return True

    except requests.HTTPError as e:
        logger.error(f"HTTP {e.response.status_code}: {e}")
    except Exception as e:
        logger.opt(exception=True).error(f"<red>未知错误: {e}</red>")

    return False


def load_keys(path: str) -> list:
    if not os.path.exists(path):
        logger.error(f"文件不存在: {path}")
        sys.exit(1)
    with open(path) as f:
        return f.readlines()

def run_all(private_keys: list, proxies: list) -> datetime:
    keys = [k.strip() for k in private_keys
            if k.strip() and not k.strip().startswith("#")]
    if not keys:
        logger.error("没有找到有效的私钥")
        sys.exit(1)

    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{now_str}] 开始每日运行")

    ok = fail = 0
    for i, key in enumerate(keys):
        proxy = proxies[i % len(proxies)] if proxies else None
        if run_wallet(key, proxy, index=i + 1, total=len(keys)):
            ok += 1
        else:
            fail += 1
        if i < len(keys) - 1:
            time.sleep(DELAY_BETWEEN_WALLETS)

    end_time = datetime.now(TZ)
    next_dt  = end_time + timedelta(hours=24)
    next_str = next_dt.strftime("%Y-%m-%d %H:%M")

    logger.info("═" * 54)
    logger.info(f"  执行完毕   成功: {ok}  失败: {fail}")
    logger.info(f"  结束时间   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  下次运行   {next_str}  (24小时后)")
    logger.info("═" * 54)

    return end_time


def sleep_with_countdown(target: datetime):
    ts = target.strftime("%Y-%m-%d %H:%M")
    logger.info(f"下次运行时间: {ts}")
    while True:
        now = datetime.now(TZ)
        secs = (target - now).total_seconds()
        if secs <= 0:
            break
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        # 动态刷新行（\r 回到行首，end='' 不换行）
        print(f"\r等待中: {h}小时 {m}分钟   ", end='', flush=True)
        time.sleep(60)
    print()  # 倒计时结束后换行
    logger.info("等待结束，开始新一轮执行")

def run_loop(keys_source, proxy_file: str):
    while True:
        keys    = load_keys(keys_source) if isinstance(keys_source, str) else keys_source
        proxies = load_proxies(proxy_file)
        end_time = run_all(keys, proxies)
        target   = end_time + timedelta(hours=24)
        sleep_with_countdown(target)


def main():
    parser = argparse.ArgumentParser(description="Simple Chain Daily Bot")
    kg = parser.add_mutually_exclusive_group()
    kg.add_argument("--key",  metavar="私钥")
    kg.add_argument("--file", metavar="文件", default=KEYS_FILE)
    parser.add_argument("--proxy-file", metavar="文件", default=PROXY_FILE)
    args = parser.parse_args()

    logger.info("=" * 54)
    logger.info("      Simple Chain Daily Bot")
    logger.info("=" * 54)

    if args.key:
        run_loop([args.key], args.proxy_file)
    else:
        run_loop(args.file, args.proxy_file)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("程序已手动停止")
        sys.exit(0)