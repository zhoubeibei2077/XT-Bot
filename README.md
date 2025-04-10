
# XT-Bot 🤖

Twitter媒体同步机器人，支持自动同步时间线/用户推文，通过Telegram Bot推送媒体内容

## 功能特性 🚀
- 定时同步近24小时的Twitter主页时间线（30分钟/次）
- Telegram Bot自动推送图文/视频（支持格式限制：图片<10M，视频<50M）
- 全量获取指定用户历史推文及媒体
- 本地化数据存储（推文数据/推送记录）
- GitHub Actions 自动化部署
- Twitter广播/空间链接推文同步到Telegram(飞书(可选))
- Telegram Bot上传异常告警信息添加飞书机器人消息通知(可选)

## 快速配置 ⚙️

### Secrets 配置项
在仓库 Settings → Secrets → Actions 中添加：

```
AUTH_TOKEN    # X（Twitter）认证Token，从浏览器Cookie获取
SCREEN_NAME   # 你的X用户名，用于获取关注列表
BOT_TOKEN     # Telegram Bot Token（通过@BotFather创建机器人获取）
CHAT_ID       # Telegram用户ID（通过@userinfobot获取）
GH_TOKEN      # GitHub API Token
REDIS_CONFIG  # Redis配置格式如下：
{
  "host": "your.redis.host",
  "port": 6379,
  "password": "your_password",
  "db": 0
}
LARK_KEY      # 飞书机器人key(可选)https://open.feishu.cn/open-apis/bot/v2/hook/{LARK_KEY}
```

> 关于 REDIS_CONFIG 补充
>
> 1. 访问 https://app.redislabs.com/ 注册账号
> 2. 创建免费数据库（30M存储空间）
> 3. 存储指定用户的键值对（例：同步@xxx时添加键值对 [screen_name:xxx]）

## 工作流程说明 ⚡

### 自动同步流程 [`XT-Bot.yml`]

- 🕒 每30分钟自动执行
- 同步最近100条时间线推文
- 自动推送媒体到Telegram

### 手动初始化流程

同步指定用户全量推文

|      工作流       |                        功能                        |
| :---------------: | :------------------------------------------------: |
| **INI-X-Bot.yml** |   ① 获取Redis配置的用户名 ② 同步用户全部历史推文   |
| **INI-T-Bot.yml** | ① 处理INI-X-Bot获取的数据 ② 批量推送媒体到Telegram |

⚠️ **注意事项**

- 在同步指定用户全量推文流程前，请先在Actions面板停用XT-Bot.yml
- 或者使用脚本执行相关流程操作，使用前需修改`sh/`目录下脚本的`REPO="your_username/XT-Bot"`

## 数据存储 🔒

```
├── Python/
│   └── output/      # Telegram推送记录
└── TypeScript/
    └── tweets/      # 推文原始数据存储
```

建议通过 [GitHub私有仓库](https://github.com/new/import) 导入项目保护隐私数据

## 技术参考 📚

- https://github.com/xiaoxiunique/x-kit
- https://github.com/fa0311/twitter-openapi-typescript

## 开源协议 📜

本项目基于 MIT License 开源

## 交流群 ✉️

https://t.me/+SYZQ5CO4oLE3ZjI1