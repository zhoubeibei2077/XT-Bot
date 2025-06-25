#!/usr/bin/env python3
import sys
import os
import json
import requests
import telegram
from pathlib import Path
import logging

# --------------------------
# 配置模块
# --------------------------
class Config:
    # 默认输入目录（存放每日推文 JSON 的 output 目录）
    DEFAULT_INPUT_DIR = "../output"
    # 目标用户
    TARGET_USER = "BayeslabsHQ"
    
    @classmethod
    def get_env_vars(cls):
        return {
            'bot_token': os.getenv('BOT_TOKEN'),
            'lark_key': os.getenv('LARK_KEY')
        }

# --------------------------
# 日志模块
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------------------------
# 通知模块
# --------------------------
class Notifier:
    @staticmethod
    def send_telegram(message: str) -> bool:
        """发送Telegram消息"""
        env = Config.get_env_vars()
        token = env.get('bot_token')
        chat_id = -8106040237  # 固定 chat_id
        
        if not token:
            logger.error("未配置 BOT_TOKEN")
            return False
        
        try:
            bot = telegram.Bot(token=token)
            bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            logger.info("✅ Telegram 消息发送成功")
            return True
        except Exception as e:
            logger.error(f"❌ Telegram 消息发送失败: {e}")
            return False
    
    @staticmethod
    def send_lark(message: str) -> bool:
        """发送飞书消息"""
        key = Config.get_env_vars().get('lark_key')
        if not key:
            logger.error("未配置 LARK_KEY")
            return False
        
        webhook = f"https://open.feishu.cn/open-apis/bot/v2/hook/{key}"
        payload = {
            "msg_type": "text",
            "content": {"text": message}
        }
        
        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("✅ Feishu 消息发送成功")
            return True
        except Exception as e:
            logger.error(f"❌ Feishu 消息发送失败: {e}")
            return False

    @staticmethod
    def send_both(message: str) -> tuple[bool, bool]:
        """同时发送到Telegram和Lark"""
        telegram_success = Notifier.send_telegram(message)
        lark_success = Notifier.send_lark(message)
        return telegram_success, lark_success

# --------------------------
# 核心处理：仅转发指定用户的推文
# --------------------------
def process_single(json_path: str) -> None:
    """处理单个JSON文件"""
    logger.info(f"开始处理: {json_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except Exception as e:
        logger.error(f"无法加载 JSON 文件 {json_path}: {e}")
        return
    
    if not isinstance(items, list):
        logger.error(f"JSON 文件格式错误，期望数组格式: {json_path}")
        return
    
    target_tweets = []
    
    # 筛选目标用户的推文
    for item in items:
        user = item.get('user', {})
        screen_name = user.get('screenName', '').strip()
        
        logger.debug(f"当前推文用户: '{screen_name}'")
        
        # 只处理指定用户的推文
        if screen_name.lower() == Config.TARGET_USER.lower():
            target_tweets.append(item)
    
    if not target_tweets:
        logger.info(f"在文件 {json_path} 中未找到用户 {Config.TARGET_USER} 的推文")
        return
    
    logger.info(f"找到 {len(target_tweets)} 条来自 {Config.TARGET_USER} 的推文")
    
    # 发送每条推文
    for i, tweet in enumerate(target_tweets, 1):
        try:
            full_text = tweet.get('fullText', '').strip()
            tweet_url = tweet.get('tweetUrl', '').strip()
            
            if not full_text and not tweet_url:
                logger.warning(f"推文 {i} 缺少内容和链接，跳过")
                continue
            
            # 构建消息内容（简化格式，只包含文本和链接）
            message_parts = []
            
            if full_text:
                message_parts.append(full_text)
            
            if tweet_url:
                message_parts.append(tweet_url)
            
            message = '\n\n'.join(message_parts)
            
            logger.info(f"准备发送推文 {i}/{len(target_tweets)}")
            
            # 同时发送到两个平台
            telegram_success, lark_success = Notifier.send_both(message)
            
            if telegram_success and lark_success:
                logger.info(f"✅ 推文 {i} 发送成功（Telegram + Lark）")
            elif telegram_success or lark_success:
                platform = "Telegram" if telegram_success else "Lark"
                logger.warning(f"⚠️ 推文 {i} 部分发送成功（仅 {platform}）")
            else:
                logger.error(f"❌ 推文 {i} 发送失败")
                
        except Exception as e:
            logger.error(f"处理推文 {i} 时出错: {e}")

# --------------------------
# 批量处理
# --------------------------
def batch_process(input_dir: str = None) -> None:
    """批量处理目录中的所有JSON文件"""
    base = Path(input_dir or Config.DEFAULT_INPUT_DIR)
    
    if not base.exists():
        logger.error(f"输入目录不存在：{base.resolve()}")
        return
    
    json_files = sorted(base.rglob('*.json'))
    
    if not json_files:
        logger.warning(f"在目录 {base.resolve()} 中未找到任何 JSON 文件")
        return
    
    logger.info(f"找到 {len(json_files)} 个 JSON 文件")
    
    for path in json_files:
        process_single(str(path))

# --------------------------
# 主入口
# --------------------------
def main():
    """主函数"""
    args = sys.argv[1:]
    
    if len(args) == 1:
        # 处理单个文件
        process_single(args[0])
    elif len(args) == 0:
        # 批量处理
        batch_process()
    else:
        logger.error("用法: python T-Bot.py [<JSON文件路径>]")
        logger.error("  无参数: 批量处理默认目录中的所有JSON文件")
        logger.error("  指定文件: 处理单个JSON文件")
        sys.exit(1)

if __name__ == "__main__":
    main()
