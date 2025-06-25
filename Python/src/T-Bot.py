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
    level=logging.DEBUG,  # 改为DEBUG级别以便调试
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
# 调试工具
# --------------------------
def debug_json_structure(json_path: str) -> None:
    """调试JSON文件结构"""
    logger.info(f"🔍 调试JSON文件结构: {json_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"📋 JSON数据类型: {type(data).__name__}")
        
        if isinstance(data, list):
            logger.info(f"📊 数组长度: {len(data)}")
            if data:
                first_item = data[0]
                logger.info(f"🔎 第一个元素类型: {type(first_item).__name__}")
                if isinstance(first_item, dict):
                    logger.info(f"🔑 第一个元素的键: {list(first_item.keys())}")
                    if 'user' in first_item:
                        user = first_item['user']
                        logger.info(f"👤 用户信息: {user}")
        elif isinstance(data, dict):
            logger.info(f"🔑 字典的键: {list(data.keys())}")
            if 'user' in data:
                user = data['user']
                logger.info(f"👤 用户信息: {user}")
        
        # 尝试找到所有用户名
        users = []
        items = []
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if 'tweets' in data:
                items = data['tweets']
            elif 'data' in data:
                items = data['data']
            else:
                items = [data]
        
        for item in items:
            if isinstance(item, dict) and 'user' in item:
                user = item['user']
                if isinstance(user, dict) and 'screenName' in user:
                    users.append(user['screenName'])
        
        if users:
            logger.info(f"👥 文件中的所有用户: {list(set(users))}")
        else:
            logger.warning("⚠️ 未找到任何用户信息")
            
    except Exception as e:
        logger.error(f"❌ 调试文件时出错: {e}")

# --------------------------
# 核心处理：仅转发指定用户的推文
# --------------------------
def process_single(json_path: str) -> None:
    """处理单个JSON文件"""
    logger.info(f"开始处理: {json_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"无法加载 JSON 文件 {json_path}: {e}")
        return
    
    # 处理不同的JSON结构
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and 'tweets' in data:
        items = data['tweets']
    elif isinstance(data, dict) and 'data' in data:
        items = data['data']
    else:
        # 如果是单个推文对象
        items = [data]
    
    logger.info(f"文件中共有 {len(items)} 条推文数据")
    
    target_tweets = []
    
    # 筛选目标用户的推文
    for i, item in enumerate(items):
        try:
            user = item.get('user', {})
            screen_name = user.get('screenName', '').strip()
            
            logger.debug(f"推文 {i+1}: 用户 = '{screen_name}'")
            
            # 只处理指定用户的推文（不区分大小写）
            if screen_name and screen_name.lower() == Config.TARGET_USER.lower():
                target_tweets.append(item)
                logger.info(f"✅ 匹配到目标用户推文: {screen_name}")
            else:
                logger.debug(f"跳过非目标用户推文: '{screen_name}'")
        except Exception as e:
            logger.error(f"处理推文 {i+1} 时出错: {e}")
    
    if not target_tweets:
        logger.info(f"在文件 {json_path} 中未找到用户 '{Config.TARGET_USER}' 的推文")
        return
    
    logger.info(f"找到 {len(target_tweets)} 条来自 '{Config.TARGET_USER}' 的推文")
    
    # 发送每条推文
    for i, tweet in enumerate(target_tweets, 1):
        try:
            full_text = tweet.get('fullText', '').strip()
            tweet_url = tweet.get('tweetUrl', '').strip()
            
            if not full_text and not tweet_url:
                logger.warning(f"推文 {i} 缺少内容和链接，跳过")
                continue
            
            # 构建消息内容（只包含文本和链接）
            message_parts = []
            
            if full_text:
                message_parts.append(full_text)
            
            if tweet_url:
                message_parts.append(tweet_url)
            
            message = '\n\n'.join(message_parts)
            
            logger.info(f"准备发送推文 {i}/{len(target_tweets)}")
            logger.debug(f"推文内容预览: {message[:100]}...")
            
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
        if args[0] == '--debug':
            # 调试模式：批量调试所有文件
            base = Path(Config.DEFAULT_INPUT_DIR)
            if base.exists():
                json_files = sorted(base.rglob('*.json'))
                for path in json_files:
                    debug_json_structure(str(path))
        else:
            process_single(args[0])
    elif len(args) == 2 and args[0] == '--debug':
        # 调试单个文件
        debug_json_structure(args[1])
    elif len(args) == 0:
        # 批量处理
        batch_process()
    else:
        logger.error("用法: python T-Bot.py [<JSON文件路径>]")
        logger.error("  无参数: 批量处理默认目录中的所有JSON文件")
        logger.error("  指定文件: 处理单个JSON文件")
        logger.error("  --debug: 调试默认目录中所有JSON文件的结构")
        logger.error("  --debug <文件路径>: 调试指定JSON文件的结构")
        sys.exit(1)

if __name__ == "__main__":
    main()
