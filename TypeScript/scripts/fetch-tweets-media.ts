import '../utils/logger';
import {cleanupLogger} from '../utils/logger';
import {processTweetsByScreenName} from './fetch-tweets';
import {processMediaByScreenName} from './fetch-media';
import {XAuthClient} from "./utils";

// 核心执行逻辑
async function main(screenName) {
    try {
        console.log('🚀 开始处理用户:', screenName);

        // 获取认证客户端
        const client = await XAuthClient();

        // 顺序执行任务
        await processTweetsByScreenName(screenName, client);
        console.log('✅ 推文处理完成');

        await processMediaByScreenName(screenName, client);
        console.log('✅ 媒体处理完成');

    } catch (error) {
        console.error('❌ 发生错误:', error instanceof Error ? error.message : error);
        process.exitCode = 1;
    } finally {
        // 统一清理资源
        await cleanupLogger();
        process.exit();
    }
}

// 获取命令行参数
const args = process.argv.slice(2);
if (args.length === 0) {
    console.error("错误：请提供用户ID作为参数");
    process.exit(1);
}

// 启动程序并传入参数
main(args[0]);