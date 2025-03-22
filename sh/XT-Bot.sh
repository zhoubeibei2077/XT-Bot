#!/bin/bash

# 功能：通过输入 0（禁用）或 1（启用）控制 XT-Bot.yml 工作流程
# 用法：运行脚本并按提示输入数字

# 固定工作流程文件名
WORKFLOW_FILE="XT-Bot.yml"

echo "获取最新状态信息..."
gh workflow list
echo "----------------------------"
# 提示用户输入
echo "请选择操作:"
echo "  [1] 启用工作流程 $WORKFLOW_FILE"
echo "  [0] 禁用工作流程 $WORKFLOW_FILE"
read -p "输入数字 (0/1): " CHOICE

# 验证输入
if [[ "$CHOICE" != "0" && "$CHOICE" != "1" ]]; then
  echo "错误：输入必须为 0 或 1！"
  exit 1
fi

# 映射操作类型
ACTION="disable"
if [ "$CHOICE" -eq 1 ]; then
  ACTION="enable"
fi

# 执行 GitHub CLI 操作
echo "正在将 $WORKFLOW_FILE 设置为 $ACTION..."
if gh workflow "$ACTION" "$WORKFLOW_FILE"; then
  echo "✅ 操作成功！等待 2 秒获取最新状态信息..."
  sleep 2  # 新增等待逻辑
  gh workflow list
else
  echo "❌ 操作失败，请检查以下可能原因:"
  echo "  1. 是否已安装 GitHub CLI (gh) 并登录 (gh auth login)"
  echo "  2. 文件 $WORKFLOW_FILE 是否存在 (gh workflow list)"
  echo "  3. 是否有仓库管理员权限"
  exit 1
fi