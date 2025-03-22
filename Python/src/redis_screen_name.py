import os
import json
import sys
import redis

def main():
    try:
        # 从环境变量获取配置
        redis_config = os.environ.get('REDIS_CONFIG')
        if not redis_config:
            raise ValueError("REDIS_CONFIG environment variable not set")

        # 解析JSON配置
        config = json.loads(redis_config)

        # 建立Redis连接
        r = redis.Redis(
            host=config.get('host', 'localhost'),
            port=config.get('port', 6379),
            password=config.get('password'),
            db=config.get('db', 0),
            decode_responses=True
        )

        # 验证连接
        if not r.ping():
            raise ConnectionError("Failed to connect to Redis")

        # 获取screen_name (关键修改点：移除所有装饰性输出)
        screen_name = r.get('screen_name')
        if not screen_name:
            raise ValueError("Key 'screen_name' not found or value is empty")

        # 纯净输出 (唯一标准输出)
        print(screen_name)

    except Exception as e:
        # 错误信息输出到stderr
        sys.stderr.write(f"ERROR:: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()