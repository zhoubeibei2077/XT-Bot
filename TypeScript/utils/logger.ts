import path from 'path';
import fs from 'fs-extra';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

// 配置时区插件
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('Asia/Shanghai'); // 设置默认时区为北京时间

// 配置日志目录和文件名格式
const LOG_DIR = path.join(__dirname, '../logs');
const LOG_FILENAME_FORMAT = 'YYYY-MM-DD';

// 确保日志目录存在
fs.ensureDirSync(LOG_DIR);

// 获取当天日志文件路径
const getLogFilePath = (): string => {
    const dateStr = dayjs().tz().format(LOG_FILENAME_FORMAT);
    return path.join(LOG_DIR, `typescript-${dateStr}.log`);
};

// 创建初始日志流（使用 let 声明）
let logStream = fs.createWriteStream(getLogFilePath(), {flags: 'a'});

// 自定义日志格式
const formatLog = (level: string, message: string): string => {
    return `[${dayjs().tz().format('YYYY-MM-DD HH:mm:ss')}] [${level.padEnd(5)}] ${message}\n`;
};

// 重写 console 方法
const originalConsoleLog = console.log;
const originalConsoleError = console.error;

console.log = (...args: any[]) => {
    const message = args.map(arg =>
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
    ).join(' ');
    originalConsoleLog(...args);
    logStream.write(formatLog('INFO', message));
};

console.error = (...args: any[]) => {
    const message = args.map(arg =>
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
    ).join(' ');
    originalConsoleError(...args);
    logStream.write(formatLog('ERROR', message));
};

// 全局错误处理
process.on('uncaughtException', (error) => {
    console.error('[全局捕获] 未处理异常:', error.message, error.stack);
    cleanupLogger();
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[全局捕获] 未处理Promise拒绝:', reason, 'at', promise);
    cleanupLogger();
    process.exit(1);
});

// 日志流错误处理
const handleStreamError = (err: Error) => {
    originalConsoleError('日志写入失败:', err.message);
};
logStream.on('error', handleStreamError);

// 新增清理函数
export function cleanupLogger() {
    return new Promise((resolve) => {
        if (logStream) {
            logStream.end(() => {
                console.log('🗑️ 日志流已正常关闭');
                resolve(true);
            });
        } else {
            resolve(true);
        }
    });
}

// 监听进程退出信号
process.on('SIGINT', async () => {
    await cleanupLogger();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    await cleanupLogger();
    process.exit(0);
});

// 当主进程正常退出时
process.on('exit', (code) => {
    console.log(`进程退出码: ${code}`);
});