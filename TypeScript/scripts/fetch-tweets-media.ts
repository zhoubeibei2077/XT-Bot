import '../utils/logger';
import {cleanupLogger} from '../utils/logger';
import {processTweetsByScreenName} from './fetch-tweets';
import {XAuthClient} from "./utils";
import fs from 'fs';
import path from 'path';

// 用户处理逻辑
async function processUser(screenName: string, client: XAuthClient) {
    try {
        console.log('🚀 开始处理用户:', screenName);

        // 使用主函数传递的客户端
        await processTweetsByScreenName(screenName, client, {
            contentType: "tweets"
        });
        console.log(`✅ [${screenName}] 推文处理完成`);

        await processTweetsByScreenName(screenName, client, {
            contentType: "media"
        });
        console.log(`✅ [${screenName}] 媒体处理完成`);

    } catch (error) {
        console.error(`❌ [${screenName}] 处理失败:`, error instanceof Error ? error.message : error);
    }
}

// 主执行程序
async function main() {

    try {
        // 初始化全局客户端
        const client = await XAuthClient();

        // 读取配置文件
        const configPath = path.resolve(__dirname, '../../config/config.json');
        if (!fs.existsSync(configPath)) {
            throw new Error(`配置文件不存在: ${configPath}`);
        }
        const configData = fs.readFileSync(configPath, 'utf-8');
        const config = JSON.parse(configData);

        // 严格校验配置结构
        if (!config || !config.screenName) {
            throw new Error('配置文件必须包含 screenName 字段');
        }

        const screenNames = config.screenName;
        if (!Array.isArray(screenNames)) {
            throw new Error('screenName 必须为数组');
        }

        for (const item of screenNames) {
            if (typeof item !== 'string') {
                console.warn(`⚠️ 跳过非字符串用户项：${typeof item} [${JSON.stringify(item)}]`);
                continue;
            }

            const screenName = item.trim();
            if (!screenName) {
                console.warn('⚠️ 跳过空用户名');
                continue;
            }

            await processUser(screenName, client);
        }

    } catch (error) {
        console.error('❌ 初始化失败:', error instanceof Error ? error.message : error);
        process.exitCode = 1;
    } finally {
        // 统一清理资源
        await cleanupLogger();
        process.exit();
    }
}

// 启动程序
main();