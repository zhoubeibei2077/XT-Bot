import json
from collections import defaultdict
import string
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# 时间转换函数
def convert_to_cst(twitter_time):
    try:
        # 解析原始时间
        utc_time = datetime.strptime(twitter_time, '%a %b %d %H:%M:%S %z %Y')
        # 转换为中国时区
        cst_time = utc_time.astimezone(ZoneInfo("Asia/Shanghai"))
        # 格式化输出
        return cst_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"时间转换错误: {e}")
        return "时间未知"

# 读取JSON数据
with open('../config/followingUser.json', 'r', encoding='utf-8') as f:
    users = json.load(f)

# 按screenName排序
sorted_users = sorted(users, key=lambda x: x['legacy']['screenName'].lower())

# 按首字母分组（支持非字母字符）
def get_first_letter(screen_name):
    first_char = screen_name[0].upper() if screen_name else "#"
    return first_char if first_char in string.ascii_uppercase else "#"

grouped = defaultdict(lambda: {"chunks": []})
for user in sorted_users:
    letter = get_first_letter(user['legacy']['screenName'])
    grouped[letter]["chunks"].append(user)

# 对每个字母组的用户进行分块（10人/组）
letters = sorted(grouped.keys())
for letter in letters:
    users_in_letter = grouped[letter]["chunks"]
    chunk_size = 10
    chunks = [
        users_in_letter[i:i + chunk_size]
        for i in range(0, len(users_in_letter), chunk_size)
    ]
    grouped[letter]["chunks"] = chunks

# 生成HTML内容
html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>X用户管理</title>
    <style>
        :root {
            --primary: #1da1f2;
            --background: #ffffff;
        }

        .created-at {
            color: #999 !important;
            font-size: 0.75em !important;
            margin: 2px 0 6px 0;
            font-family: monospace;
            opacity: 0.8;
        }

        .letter-section::before {
            content: "";
            display: block;
            height: 30px;
            margin-top: -30px;
            padding-top: 30px;
            visibility: hidden;
        }

        body {
            font-family: -apple-system, system-ui, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f3f5;
        }

        .nav-bar {
            position: sticky;
            top: 0;
            background: var(--background);
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 100;
        }

        .nav-letter {
            display: inline-block;
            margin: 0 4px;
            padding: 6px 12px;
            border-radius: 4px;
            background: #f0f3f5;
            color: var(--primary);
            text-decoration: none;
            transition: all 0.2s;
        }

        .nav-letter:hover {
            background: var(--primary);
            color: white;
        }

        .letter-section {
            margin: 25px 0;
            background: var(--background);
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }

        .group-header {
            padding: 16px;
            border-bottom: 1px solid #eee;
            font-size: 1.1em;
            color: var(--primary);
        }

        .user-group {
            padding: 16px;
            border-top: 2px dashed #eee;
        }

        .group-title {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 12px;
        }

        .group-index {
            font-size: 0.9em;
            color: #657786;
        }

        /* 新增按钮样式 */
        .open-group-btn {
            padding: 6px 15px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 0.9em;
        }

        .open-group-btn:hover {
            background: #166dab;
        }

        .user-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(160px, 1fr));
            gap: 12px;
        }

        @media (max-width: 1440px) {
            .user-grid { grid-template-columns: repeat(4, minmax(160px, 1fr)); }
        }

        @media (max-width: 1024px) {
            .user-grid { grid-template-columns: repeat(3, minmax(140px, 1fr)); }
        }

        @media (max-width: 768px) {
            .user-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
        }

        @media (max-width: 480px) {
            .user-grid { grid-template-columns: 1fr; }
        }

        .user-card {
            min-width: 160px;
            padding: 12px;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            background: var(--background);
            transition: transform 0.2s;
            box-sizing: border-box;
        }

        .user-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }

        .screen-name {
            color: var(--primary);
            font-weight: 600;
            text-decoration: none;
            display: block;
            margin-top: 8px;
            font-size: 0.9em;
        }

        .user-id {
            color: #657786;
            font-size: 0.8em;
        }
    </style>
    <script>
        function openGroup(groupId) {
            const links = document.querySelectorAll(
                `#group-${groupId} .screen-name`
            );

            // 先打开第一个链接触发授权
            if(links.length > 0) {
                window.open(links[0].href, '_blank');
            }

            // 延迟打开剩余链接
            setTimeout(() => {
                links.forEach((link, index) => {
                    if(index === 0) return; // 跳过第一个已打开的
                    setTimeout(() => {
                        window.open(link.href, '_blank');
                    }, (index - 1) * 300);
                });
            }, 1000);
        }
    </script>
</head>
<body>
<nav class="nav-bar">
    {nav_letters}
</nav>

<h1>X用户列表（共 {total} 人）</h1>

{letter_sections}
</body>
</html>
'''

# 生成导航字母
nav_letters = []
for letter in sorted(letters):
    nav_letters.append(f'<a href="#{letter}" class="nav-letter">{letter}</a>')
nav_letters_html = "\n    ".join(nav_letters)

# 生成字母区块
letter_sections = []
global_group_index = 0  # 全局分组计数器
for letter in letters:
    section = f'''
    <section class="letter-section" id="{letter}">
        <div class="group-header">
            {letter} 分组（{len(grouped[letter]["chunks"])} 组）
        </div>'''

    for chunk_index, chunk in enumerate(grouped[letter]["chunks"], 1):
        global_group_index += 1
        section += f'''
        <div class="user-group" id="group-{global_group_index}">
            <div class="group-title">
                <span class="group-index">第 {chunk_index} 组（{len(chunk)} 人）</span>
                <button
                    class="open-group-btn"
                    onclick="openGroup({global_group_index})"
                >一键打开本组</button>
            </div>
            <div class="user-grid">'''

        for user in chunk:
            legacy = user['legacy']
            created_at = convert_to_cst(legacy.get('createdAt', ''))
            section += f'''
                <div class="user-card">
                    <div class="user-id">ID: {user['restId']}</div>
                    <div class="name">{legacy['name']}</div>
                    <div class="created-at">注册时间: {created_at}</div>
                    <a href="https://x.com/{legacy['screenName']}"
                       class="screen-name"
                       target="_blank">
                        @{legacy['screenName']}
                    </a>
                </div>'''

        section += '''
            </div>
        </div>'''

    section += '''
    </section>'''
    letter_sections.append(section)

# 替换模板变量
final_html = html_content.replace("{nav_letters}", nav_letters_html)\
    .replace("{total}", str(len(sorted_users)))\
    .replace("{letter_sections}", "\n".join(letter_sections))

# 保存文件
with open('../config/user_card.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print("用户卡片网页 user_card.html 生成成功！")