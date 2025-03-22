import {XAuthClient} from "./utils";
import path from 'path';
import fs from "fs-extra";
import {get} from 'lodash'; // 添加lodash.get安全访问

console.log(`----- ----- ----- ----- fetch-following begin ----- ----- ----- -----`);
try {
    const client = await XAuthClient();

    const screenName = process.env.SCREEN_NAME;
    if (!screenName) {
        throw new Error("❌ SCREEN_NAME 环境变量未配置");
    }
    console.log(`🌐 正在请求API获取用户信息：@${screenName}`);
    const response = await client.getUserApi().getUserByScreenName({screenName});
    if (!response.data?.user?.restId) {
        throw new Error(`❌ 用户 @${screenName} 存在但无法获取有效ID`);
    }

    const userId = response.data.user.restId;
    const outputPath = `../../Python/config/followingUser.json`;

    const outputDir = path.dirname(outputPath);
    fs.ensureDirSync(outputDir);

    let cursor: string | undefined;
    let allUsers = [];
    let pageCount = 0;
    let emptyCount = 0;
    const requestInterval = 5000;

    do {
        pageCount++;
        console.log(`\n=== 第 ${pageCount} 次请求 ===`);

        // 添加间隔控制（第一页后生效）
        if (pageCount > 1) {
            console.log(`⏸️ 等待 ${requestInterval / 1000} 秒...`);
            await new Promise(r => setTimeout(r, requestInterval));
        }

        const resp = await client.getUserListApi().getFollowing({
            userId,
            cursor,
            count: 20
        });

        // 提取有效用户数据
        const rawItems = get(resp, 'data.data', []);
        const currentCursor = get(resp, 'data.cursor.bottom.value', null);

        // 转换数据结构
        const validUsers = rawItems
            .map(item => get(item, 'user', null))  // 使用lodash.get安全取值
            .filter(user => user && typeof user === 'object');  // 过滤无效用户

        if (validUsers.length === 0) {
            emptyCount++;
            console.log(`⚠️ 空响应计数: ${emptyCount}/3`);
            if (emptyCount >= 3) {
                console.log("⏹️ 终止原因：连续3次空响应");
                break;
            }
        } else {
            emptyCount = 0; // 重置计数器
            allUsers.push(...validUsers);
        }

        // 更新游标
        cursor = currentCursor;
        console.log(`✅ 获取到 ${validUsers.length} 用户 | 游标: ${cursor || '无'}`);

    } while (true); // 改为由内部条件控制

    // 数据写入
    await fs.writeFile(outputPath, JSON.stringify(allUsers, null, 2));
    console.log(`\n🎉 完成！共获取 ${allUsers.length} 个用户`);

} catch (error) {
    console.error('处理失败:', error.message);
    process.exit(1);
}
console.log(`----- ----- ----- ----- fetch-following end ----- ----- ----- -----`);