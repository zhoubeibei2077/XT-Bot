import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 分片参数
MAX_ENTRIES_PER_SHARD = 10000  # 每个分片最多存储10000条记录
SHARD_DIR = '../dataBase/'     # 分片存储目录
FORMAT_SHARDS = True           # 是否格式化分片文件（True: 可读格式，False: 高性能紧凑格式）

def get_entry_id(entry):
    """生成媒体条目的唯一标识符"""
    return f"{entry['file_name']}_{entry['user']['screenName']}_{entry['media_type']}"

def get_shard_files():
    """获取所有分片文件路径"""
    if not os.path.exists(SHARD_DIR):
        os.makedirs(SHARD_DIR)
    files = []
    for filename in os.listdir(SHARD_DIR):
        if filename.startswith("processed_entries_") and filename.endswith(".json"):
            files.append(os.path.join(SHARD_DIR, filename))
    return files

def parse_shard_number(file_path):
    """从文件名中解析分片编号"""
    basename = os.path.basename(file_path)
    parts = basename.split('_')[-1].split('.')[-2].split('-')
    return int(parts[-1]) if len(parts) > 0 else 0

def get_max_shard_number(year_month):
    """获取指定年月的最大分片编号"""
    max_num = 0
    for file_path in get_shard_files():
        if f"_{year_month}-" in file_path:
            num = parse_shard_number(file_path)
            if num > max_num:
                max_num = num
    return max_num

def save_entry(entry_id):
    """将条目ID保存到分片文件"""
    year_month = datetime.now().strftime("%Y-%m")
    current_max_shard = get_max_shard_number(year_month)
    current_shard = current_max_shard + 1

    candidate_path = os.path.join(
        SHARD_DIR,
        f"processed_entries_{year_month}-{current_max_shard:04d}.json"
    )

    if os.path.exists(candidate_path):
        try:
            with open(candidate_path, 'r') as f:
                entries = json.load(f)
            if len(entries) < MAX_ENTRIES_PER_SHARD:
                entries.append(entry_id)
                with open(candidate_path, 'w') as f:
                    if FORMAT_SHARDS:
                        json.dump(entries, f, indent=2)
                    else:
                        json.dump(entries, f)
                return candidate_path
        except json.JSONDecodeError:
            logger.warning(f"警告：分片文件损坏，尝试重写：{candidate_path}")
            with open(candidate_path, 'w') as f:
                if FORMAT_SHARDS:
                    json.dump([entry_id], f, indent=2)
                else:
                    json.dump([entry_id], f)
            return candidate_path

    # 创建新分片
    shard_filename = f"processed_entries_{year_month}-{current_shard:04d}.json"
    shard_path = os.path.join(SHARD_DIR, shard_filename)
    with open(shard_path, 'w') as f:
        if FORMAT_SHARDS:
            json.dump([entry_id], f, indent=2)
        else:
            json.dump([entry_id], f)
    return shard_path

def load_processed_entries():
    """加载所有已处理的条目ID集合"""
    processed = set()
    for file_path in get_shard_files():
        try:
            with open(file_path, 'r') as f:
                entries = json.load(f)
                if isinstance(entries, list):
                    processed.update(entries)
                else:
                    logger.warning(f"警告：分片文件 {file_path} 格式不正确（非列表类型），已跳过")
        except json.JSONDecodeError:
            logger.warning(f"警告：分片文件损坏：{file_path}，已跳过")
        except Exception as e:
            logger.error(f"错误读取分片文件 {file_path}: {str(e)}，已跳过")
    return processed

def main(data_file, config_file, output_file):

    logger.info("🎬 开始处理推文")
    logger.info(f"📁 JSON路径: {data_file}")
    logger.info(f"📥 导出目录: {output_file}")

    # 确保分片目录存在
    if not os.path.exists(SHARD_DIR):
        os.makedirs(SHARD_DIR)

    # 读取配置文件
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        users_to_query = [user["legacy"]["screenName"] for user in config]
        if not users_to_query:
            logger.warning("配置文件中未指定要查询的用户！")
            return
    except FileNotFoundError:
        logger.error(f"错误：配置文件 {config_file} 未找到！")
        return
    except json.JSONDecodeError:
        logger.error(f"错误：配置文件 {config_file} 格式不正确！")
        return

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    # 加载所有分片中的条目ID
    processed_entries = load_processed_entries()

    # 读取并解析输入数据文件
    user_data = {}
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            users_list = json.load(f)

            for user_entry in users_list:
                user = user_entry.get("user", {})
                screen_name = user.get("screenName")
                if not screen_name:
                    logger.warning(f"警告：用户对象缺少screenName字段，跳过 {user_entry}")
                    continue

                if screen_name not in user_data:
                    user_data[screen_name] = {
                        "name": user.get("name", "N/A"),
                        "entries": []
                    }

                entry = {
                    "fullText": user_entry.get("fullText", ""),
                    "publishTime": user_entry.get("publishTime", ""),
                    "images": list(user_entry.get("images", [])),
                    "videos": list(user_entry.get("videos", []))
                }
                user_data[screen_name]["entries"].append(entry)

    except FileNotFoundError:
        logger.error(f"错误：数据文件 {data_file} 未找到！")
        return
    except json.JSONDecodeError as e:
        logger.error(f"错误：数据文件格式不正确！{str(e)}")
        return

    # 生成新条目（全局去重）
    new_entries = []
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for target in users_to_query:
        user_info = user_data.get(target)
        if not user_info:
            continue

        for entry in user_info["entries"]:
            full_text = entry["fullText"]
            publish_time = entry["publishTime"]
            for media_type in ["images", "videos"]:
                media_list = entry.get(media_type, [])
                for media_url in media_list:
                    filename = media_url.split("?")[0].split("/")[-1]
                    entry_id = f"{filename}_{target}_{media_type}"

                    # 检查是否已处理过（全局去重）
                    if entry_id in processed_entries:
                        continue

                    # 创建新条目，初始状态
                    new_entry = {
                        "file_name": filename,
                        "user": {
                            "screenName": target,
                            "name": user_info["name"]
                        },
                        "media_type": media_type,
                        "url": media_url,
                        "read_time": current_time,  # 仅首次处理时记录
                        "is_uploaded": False,
                        "upload_info": {},
                        "is_downloaded": False,
                        "download_info": {},
                        "fullText": full_text,
                        "publishTime": publish_time
                    }

                    new_entries.append(new_entry)
                    # 标记为已处理
                    save_entry(entry_id)

    # 合并新旧输出文件（仅添加新条目）
    try:
        existing_entries = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_entries = json.load(f)
    except Exception as e:
        logger.warning(f"警告：读取现有输出文件失败：{str(e)}")
        existing_entries = []

    # 合并逻辑：保留所有现有条目，仅添加新条目
    merged_entries = existing_entries.copy()
    existing_entry_ids = {get_entry_id(e) for e in existing_entries}

    new_count = 0
    for new_entry in new_entries:
        entry_id = get_entry_id(new_entry)
        if entry_id not in existing_entry_ids:
            merged_entries.append(new_entry)
            new_count += 1

    # 修改排序逻辑：处理可能缺失的字段
    merged_entries.sort(key=lambda x: x.get('publishTime', '1970-01-01T00:00:00'))

    # 写入输出文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            if FORMAT_SHARDS:
                json.dump(merged_entries, f, indent=2, ensure_ascii=False)
            else:
                json.dump(merged_entries, f, ensure_ascii=False)

        # 打印统计信息
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 新增条目数: {new_count}")
    except Exception as e:
        logger.error(f"写入文件时出错：{str(e)}")

if __name__ == "__main__":
    if len(sys.argv) == 4:  # 脚本名 + 3个参数
        data_file = os.path.normpath(sys.argv[1])
        config_file = os.path.normpath(sys.argv[2])
        output_file = os.path.normpath(sys.argv[3])
        # 如果文件不存在则跳过
        if os.path.exists(data_file):
            main(data_file, config_file, output_file)
        else:
            logger.info(f"文件不存在，已跳过：{data_file}")
    elif len(sys.argv) == 2:  # 脚本名 + 数据文件
        data_file = os.path.normpath(sys.argv[1])
        current_date = datetime.now()
        config_file = os.path.normpath("../config/followingUser.json")

        # 输出文件路径
        output_file = os.path.normpath(
            f"../output/"
            f"{current_date:%Y-%m}/{current_date:%Y-%m-%d}.json"
        )

        # 如果文件不存在则跳过
        if os.path.exists(data_file):
            main(data_file, config_file, output_file)
        else:
            logger.info(f"文件不存在，已跳过：{data_file}")
    elif len(sys.argv) == 1:  # 仅脚本名
        # 默认处理今天和昨天
        current_date = datetime.now()
        config_file = os.path.normpath("../config/followingUser.json")

        for day_offset in range(8):  # 一周
            target_date = current_date - timedelta(days=day_offset)

            # 推文数据文件路径
            data_file = os.path.normpath(
                f"../../TypeScript/tweets/"
                f"{target_date:%Y-%m}/{target_date:%Y-%m-%d}.json"
            )

            # 输出文件路径
            output_file = os.path.normpath(
                f"../output/"
                f"{target_date:%Y-%m}/{target_date:%Y-%m-%d}.json"
            )

            # 如果文件不存在则跳过
            if os.path.exists(data_file):
                main(data_file, config_file, output_file)
            else:
                logger.info(f"文件不存在，已跳过：{data_file}")
    else:
        logger.error("错误：参数数量不正确")
        logger.info("使用方法：python X-Bot.py [<推文数据文件> <配置文件> <输出文件>]")
        logger.info("示例：")
        logger.info("带参数：python X-Bot.py ../../TypeScript/tweets/2000-01/2000-01-01.json ../config/followingUser.json ../output/2000-01/2000-01-01.json")
        logger.info("用默认：python X-Bot.py")
        sys.exit(1)
