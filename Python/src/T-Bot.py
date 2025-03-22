import sys
import json
import os
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
import telegram
from telegram.error import TelegramError, BadRequest

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Telegram文件限制（单位：字节）
TELEGRAM_LIMITS = {
    'images': 10 * 1024 * 1024,  # 10MB
    'videos': 50 * 1024 * 1024   # 50MB
}

class FileTooLargeError(Exception):
    """自定义文件过大异常"""
    pass

def main(json_path, download_dir):
    """主处理函数"""
    try:
        logger.info("🎬 开始处理媒体文件")
        logger.info(f"📁 JSON路径: {json_path}")
        logger.info(f"📥 下载目录: {download_dir}")

        # 初始化配置
        bot = telegram.Bot(token=os.environ['BOT_TOKEN'])
        chat_id = os.environ['CHAT_ID']
        download_path = Path(download_dir)

        # 确保下载目录存在
        download_path.mkdir(parents=True, exist_ok=True)

        # 加载并处理数据
        with open(json_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            total = len(data)

            for index, item in enumerate(data, 1):
                file_name = item['file_name']

                # 处理下载
                if not item['is_downloaded']:
                    # 检查当前尝试次数
                    current_attempts = item.get('download_info', {}).get('download_attempts', 0)
                    if current_attempts >= 10:
                        logger.warning(f"⏭ 已达最大下载尝试次数，跳过: {item['file_name']}")
                    else:
                        handle_download(item, download_path)

                # 处理上传
                if should_upload(item):
                    handle_upload(item, bot, chat_id, download_path)

            # 保存更新后的数据
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()

        logger.info("✅ 所有文件处理完成")

    except Exception as e:
        logger.error(f"💥 发生全局错误: {str(e)}", exc_info=True)
        raise

def handle_download(item, download_path):
    """处理文件下载"""
    file_name = item['file_name']
    try:
        logger.info(f"⏬ 开始下载: {file_name}")

        response = requests.get(item['url'], stream=True, timeout=30)
        response.raise_for_status()

        file_path = download_path / file_name
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 更新下载状态
        file_size = os.path.getsize(file_path)
        item.update({
            "is_downloaded": True,
            "download_info": {
                "success": True,
                "size": file_size,
                "size_mb": round(file_size/1024/1024, 2),  # 新增MB单位
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),  # 去除毫秒
                "download_attempts": 0  # 重置计数器
            }
        })

        logger.info(f"✓ 下载成功: {file_name} ({file_size//1024}KB)")

    except Exception as e:
        # 获取当前下载尝试次数
        current_attempts = item.get('download_info', {}).get('download_attempts', 0)
        new_attempts = current_attempts + 1

        error_msg = f"✗ 下载失败: {file_name} - {str(e)}"
        logger.error(error_msg)

        # 创建新的错误信息
        error_info = create_error_info(e, "download_error")
        error_info["download_attempts"] = new_attempts  # 更新尝试次数

        # 设置下载信息
        item['download_info'] = error_info

        # 检查是否达到最大尝试次数
        if new_attempts >= 10:
            logger.error(f"‼️ 达到最大下载尝试次数: {file_name}")
            item['upload_info'] = create_error_info(
                Exception(f"连续下载失败{new_attempts}次"),
                "max_download_attempts"
            )
            item['is_uploaded'] = False

def should_upload(item):
    """判断是否需要上传"""
    if item.get('is_uploaded'):
        return False

    # 检查不可恢复的错误
    error_type = item.get('upload_info', {}).get('error_type')
    if error_type in ['file_too_large', 'max_download_attempts']:
        logger.warning(f"⏭ 跳过不可恢复的错误: {item['file_name']} ({error_type})")
        return False

    if not item.get('is_downloaded'):
        logger.warning("✗ 当前文件下载失败")
        return False
    return True

def handle_upload(item, bot, chat_id, download_path):
    """处理文件上传"""
    file_name = item['file_name']
    try:
        file_path = download_path / file_name
        file_size = item['download_info']['size']
        logger.info(f"📤 准备上传: {file_name} ({file_size//1024//1024}MB)")

        # 预检文件大小（使用自定义异常）
        if item['media_type'] == 'images' and file_size > TELEGRAM_LIMITS['images']:
            raise FileTooLargeError(f"图片过大 ({file_size//1024//1024}MB > 10MB)")
        elif item['media_type'] == 'videos' and file_size > TELEGRAM_LIMITS['videos']:
            raise FileTooLargeError(f"视频过大 ({file_size//1024//1024}MB > 50MB)")

        # 构建caption
        user_info = f"#{item['user']['screenName']} {item['user']['name']}"
        publishTime = datetime.fromisoformat(item['publishTime']).strftime("%Y-%m-%d %H:%M:%S")
        raw_caption = f"{user_info}\n{publishTime}\n{item['fullText']}"

        # 智能截断逻辑：优先保留用户信息和时间
        max_length = 1024
        if len(raw_caption) > max_length:
            remaining = max_length - len(user_info) - len(publishTime) - 2  # -2 for newlines
            caption = f"{user_info}\n{publishTime}\n{item['fullText'][:remaining]}"
        else:
            caption = raw_caption

        # 执行上传
        with open(file_path, 'rb') as f:
            if item['media_type'] == 'images':
                msg = bot.send_photo(chat_id=chat_id, photo=f, caption=caption)
                media_type = "图片"
            else:
                msg = bot.send_video(chat_id=chat_id, video=f, caption=caption)
                media_type = "视频"

        # 更新上传状态
        item.update({
            "is_uploaded": True,
            "upload_info": {
                "success": True,
                "message_id": msg.message_id,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            }
        })

        logger.info(f"✓ 上传成功: {media_type} {file_name} (消息ID: {msg.message_id})")

    except FileTooLargeError as e:
        logger.error(f"✗ 文件大小超标: {file_name} - {str(e)}")
        item['upload_info'] = create_error_info(e, 'file_too_large')
        item['is_downloaded'] = False
    except BadRequest as e:
        if 'too large' in str(e).lower():
            logger.error(f"✗ Telegram文件限制: {file_name} - {str(e)}")
            item['upload_info'] = create_error_info(e, 'file_too_large')
        else:
            logger.error(f"✗ Telegram API错误: {file_name} - {str(e)}")
            item['upload_info'] = create_error_info(e, 'api_error')
        item['is_downloaded'] = False
    except TelegramError as e:
        logger.error(f"✗ Telegram协议错误: {file_name} - {str(e)}")
        item['upload_info'] = create_error_info(e, 'api_error')
        item['is_downloaded'] = False
    except Exception as e:
        logger.error(f"✗ 未知上传错误: {file_name} - {str(e)}")
        item['upload_info'] = create_error_info(e, 'temporary_error')
        item['is_downloaded'] = False

def create_error_info(error, error_type):
    """创建标准错误信息"""
    return {
        "success": False,
        "error_type": error_type,
        "message": str(error),
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }

if __name__ == "__main__":
    if len(sys.argv) == 3:
        # 使用命令行参数
        json_path = os.path.normpath(sys.argv[1])
        download_dir = os.path.normpath(sys.argv[2])
        # 如果文件不存在则跳过
        if os.path.exists(json_path):
            main(json_path, download_dir)
        else:
            logger.info(f"文件不存在，已跳过：{json_path}")
    elif len(sys.argv) == 1:
        # 默认处理今天和昨天
        current_date = datetime.now()
        download_dir = os.path.normpath("../downloads")

        for day_offset in range(8):  # 一周
            target_date = current_date - timedelta(days=day_offset)

            # 数据文件路径
            json_path = os.path.normpath(
                f"../output/{target_date:%Y-%m}/{target_date:%Y-%m-%d}.json"
            )

            # 如果文件不存在则跳过
            if os.path.exists(json_path):
                main(json_path, download_dir)
            else:
                logger.info(f"文件不存在，已跳过：{json_path}")
    else:
        logger.error("错误：参数数量不正确。")
        logger.info("使用方法：python T-Bot.py [<JSON文件路径> <下载目录>]")
        logger.info("示例：")
        logger.info("使用参数：python T-Bot.py ../output/2000-01/2000-01-01.json ../downloads")
        logger.info("使用默认：python T-Bot.py")
        sys.exit(1)
