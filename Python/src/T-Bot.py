#!/usr/bin/env python3
import sys
import os
import json
import requests
import telegram
from pathlib import Path
from datetime import datetime

# --------------------------
# 配置模块
# --------------------------
class Config:
    MESSAGE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    # 默认输入目录（存放每日推文 JSON 的 output 目录）
    DEFAULT_INPUT_DIR = "../output"

    @classmethod
    def get_env_vars(cls):
        return {
            'bot_token': os.getenv('BOT_TOKEN'),
            'lark_key': os.getenv('LARK_KEY')
        }

# --------------------------
# 日志模块（简化）
# --------------------------
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------
# 通知模块
# --------------------------
class Notifier:
    @staticmethod
    def send_telegram(message: str) -> bool:
        env = Config.get_env_vars()
        token = env.get('bot_token')
        chat_id = -8106040237  # 固定 chat_id
        if not token:
            logger.error("未配置 BOT_TOKEN")
            return False
        bot = telegram.Bot(token=token)
        try:
            bot.send_message(chat_id=chat_id, text=message)
            logger.info("✅ Telegram 消息发送成功")
            return True
        except Exception as e:
            logger.error(f"❌ Telegram 消息发送失败: {e}")
            return False

    @staticmethod
    def send_lark(message: str) -> bool:
        key = Config.get_env_vars().get('lark_key')
        if not key:
            return False
        webhook = f"https://open.feishu.cn/open-apis/bot/v2/hook/{key}"
        payload = {"msg_type": "text", "content": {"text": message}}
        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("✅ Feishu 消息发送成功")
            return True
        except Exception as e:
            logger.error(f"❌ Feishu 消息发送失败: {e}")
            return False

# --------------------------
# 核心处理：仅转发指定用户的推文
# --------------------------
TARGET_USER = "BayeslabsHQ"

def process_single(json_path: str) -> None:
    logger.info(f"开始处理: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except Exception as e:
        logger.error(f"无法加载 JSON 文件 {json_path}: {e}")
        return

    for item in items:
        user = item.get('user', {})
        screen_name = user.get('screenName', '').strip()
        logger.debug(f"当前推文用户: '{screen_name}'")
        if screen_name.lower() != TARGET_USER.lower():
            continue  # 只处理指定用户

        logger.info(f"匹配到目标用户: {screen_name}，准备发送消息")
        raw_time = item.get('publishTime', '')[:19]
        publish_time = raw_time.replace('T', ' ')
        text = item.get('fullText', '')
        url = item.get('tweetUrl', '')
        message = f"#{screen_name}\n{publish_time}\n{text}\n{url}"

        Notifier.send_telegram(message)
        Notifier.send_lark(message)

# --------------------------
# 批量处理
# --------------------------

def batch_process(input_dir: str = None) -> None:
    base = Path(input_dir or Config.DEFAULT_INPUT_DIR)
    if not base.exists():
        logger.error(f"输入目录不存在：{base.resolve()}")
        return

    json_files = sorted(base.rglob('*.json'))
    if not json_files:
        logger.warning(f"在目录 {base.resolve()} 中未找到任何 JSON 文件")
        return

    for path in json_files:
        process_single(str(path))

# --------------------------
# 主入口
# --------------------------

def main():
    args = sys.argv[1:]
    if len(args) == 1:
        process_single(args[0])
    elif len(args) == 0:
        batch_process()
    else:
        logger.error("用法: python T-Bot.py [<JSON文件路径>]")
        sys.exit(1)

if __name__ == "__main__":
    main()
