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
            logger.info("Telegram 消息发送成功")
            return True
        except Exception as e:
            logger.error(f"Telegram 消息发送失败: {e}")
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
            logger.info("Feishu 消息发送成功")
            return True
        except Exception as e:
            logger.error(f"Feishu 消息发送失败: {e}")
            return False

# --------------------------
# 核心处理
# --------------------------
def process_single(json_path: str) -> None:
    logger.info(f"开始处理: {json_path}")
    # 加载 JSON 数据
    with open(json_path, 'r', encoding='utf-8') as f:
        items = json.load(f)

    for item in items:
        # 构建文本和链接
        screen_name = item['user']['screen_name']
        publish_time = datetime.fromisoformat(item['publish_time']).strftime(Config.MESSAGE_DATE_FORMAT)
        text = item.get('full_text', '')
        url = item.get('url', '')
        message = f"#{screen_name}\n{publish_time}\n{text}\n{url}"

        # 发送到 Telegram
        Notifier.send_telegram(message)
        # 发送到 Feishu
        Notifier.send_lark(message)

# --------------------------
# 主入口
# --------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("用法: python T-Bot-text-only.py <JSON文件路径>")
        sys.exit(1)
    process_single(sys.argv[1])
