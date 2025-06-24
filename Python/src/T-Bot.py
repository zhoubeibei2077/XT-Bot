#!/usr/bin/env python3
import sys
import os
import json
import glob
import requests
import telegram
from pathlib import Path
from datetime import datetime

# --------------------------
# 配置模块
# --------------------------
class Config:
    MESSAGE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def get_env_vars(cls):
        return {
            'bot_token': os.getenv('BOT_TOKEN'),
            'chat_id': os.getenv('CHAT_ID'),
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
        if not env['bot_token'] or not env['chat_id']:
            logger.error("未配置 BOT_TOKEN 或 CHAT_ID")
            return False
        bot = telegram.Bot(token=env['bot_token'])
        try:
            bot.send_message(chat_id=env['chat_id'], text=message)
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
# 核心处理
# --------------------------
def process_single(json_path: str) -> None:
    logger.info(f"开始处理: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except Exception as e:
        logger.error(f"无法加载 JSON 文件 {json_path}: {e}")
        return

    for item in items:
        screen_name = item.get('user', {}).get('screen_name', 'unknown')
        # 兼容 ISO 格式时间，取前 19 字符并替换 T 为 空格
        raw_time = item.get('publish_time', '')[:19]
        try:
            publish_time = raw_time.replace('T', ' ')
        except Exception:
            publish_time = raw_time
        text = item.get('full_text', '')
        url = item.get('url', '')
        message = f"#{screen_name}\n{publish_time}\n{text}\n{url}"

        Notifier.send_telegram(message)
        Notifier.send_lark(message)

# --------------------------
# 批量处理
# --------------------------
def batch_process(directory: str = '.') -> None:
    json_files = sorted(Path(directory).glob('*.json'))
    if not json_files:
        logger.warning(f"在目录 {directory} 中未找到任何 JSON 文件")
        return
    for path in json_files:
        process_single(str(path))

# --------------------------
# 主入口
# --------------------------
def main():
    args = sys.argv[1:]
    if len(args) == 1:
        # 处理指定文件
        process_single(args[0])
    elif len(args) == 0:
        # 没有参数则批量处理当前目录下所有 JSON
        batch_process()
    else:
        logger.error("用法: python T-Bot-text-only.py [<JSON文件路径>]")
        sys.exit(1)

if __name__ == "__main__":
    main()
