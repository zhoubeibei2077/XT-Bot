# XT-Bot 🤖

爬取Twitter推文和媒体，支持主页时间线/用户推文，通过Telegram Bot推送媒体内容

## 功能特性 🚀

- 定时同步Twitter主页时间线推文（30分钟/次）
- 同步指定用户全量历史推文及媒体（支持多用户）
- Telegram Bot自动推送图文/视频（支持格式限制：图片<10M，视频<50M）
- 本地化数据存储（推文数据/推送记录）
- GitHub Actions 自动化部署
- Twitter广播/空间链接推文同步到Telegram(飞书(可选))
- 操作异常告警信息添加飞书机器人消息通知(可选)

## 快速配置 ⚙️

### Secrets 配置项

在仓库 Settings → Secrets → Actions → Repository secrets 中添加：

```
AUTH_TOKEN    # X（Twitter）认证Token，从浏览器Cookie获取
SCREEN_NAME   # 你的X用户名，用于获取关注列表
BOT_TOKEN     # Telegram Bot Token（通过@BotFather创建机器人获取）
CHAT_ID       # Telegram用户ID（通过@userinfobot获取）
GH_TOKEN      # GitHub API Token
REDIS_CONFIG  # Redis配置(可选)格式如下：
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
> 3. 存储运行相关配置，需手动添加key值【config】，对应项目的 config/config.json 文件中配置项

## 工作流程说明 ⚡

### 自动同步流程 [`XT-Bot.yml`]

- 🕒 每30分钟自动执行
- 同步最近24小时的主页时间线推文
- 过滤广告等非关注用户推文
- 支持相关参数配置请求
- 自动推送媒体到Telegram Bot

### 手动初始化流程 [`INI-XT-Bot.yml`]

同步指定用户全量推文（支持多用户） 在 config/config.json 中添加用户信息，执行相关流程操作

下面详细介绍一下可配置项（可通过redis的key键config来修改）

- interval: 请求间隔（默认5000ms）
- filterRetweets: 是否过滤转发推文（默认true）
- filterQuotes: 是否过滤引用推文（默认true）
- limit: 同步推文数量（默认不限制）
- screenName: 同步用户列表（例：同步@xxx时添加"xxx"）

示例如下

```json
{
  "interval": 5000,
  "filterRetweets": true,
  "filterQuotes": false,
  "limit": 2000,
  "screenName": [
    "xxx"
  ]
}
```

⚠️ **注意事项**

- 在同步指定用户全量推文流程前，请先在Actions面板停用XT-Bot.yml
- 或者使用`sh/`目录下`INI-XT-Bot.sh`(macOS)脚本执行相关流程操作，使用前需修改`REPO="your_username/XT-Bot"`

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