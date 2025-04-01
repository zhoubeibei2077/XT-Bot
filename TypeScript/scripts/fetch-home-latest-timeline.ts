import {XAuthClient} from "./utils";
import {formatDateToLocalISO} from "./utils";
import {get} from "lodash";
import dayjs from "dayjs";
import fs from "fs-extra";
import type {TweetApiUtilsData} from "twitter-openapi-typescript";

console.log(`----- ----- ----- ----- fetch-home-latest-timeline begin ----- ----- ----- -----`);
const client = await XAuthClient();

console.log(`🔄 开始获取首页最新时间线...`);
const resp = await client.getTweetApi().getHomeLatestTimeline({
    count: 100,
});
console.log(`✅ 成功获取首页最新时间线，原始推文数量：${resp.data.data.length}条`);

// 过滤出原创推文
const originalTweets = resp.data.data.filter((tweet) => {
    return !tweet.referenced_tweets || tweet.referenced_tweets.length === 0;
});

// 获取关注用户列表
const followingConfig = `../../Python/config/followingUser.json`;
console.log(`📂 读取关注用户配置文件：${followingConfig}...`);
const followingJson = JSON.parse(await fs.readFile(followingConfig, 'utf-8'));
const restIds = followingJson.map(item => item.restId);
console.log(`👥 共获取到${restIds.length}个关注用户`);

const rows: TweetApiUtilsData[] = [];
console.log("🔧 开始处理推文数据，过滤非关注用户及1天外的推文...");

// 输出所有原创推文的访问地址
originalTweets.forEach((tweet) => {
    const isQuoteStatus = get(tweet, "raw.result.legacy.isQuoteStatus");
    if (isQuoteStatus) {
        return;
    }
    const fullText = get(tweet, "raw.result.legacy.fullText", "RT @");
    if (fullText?.includes("RT @")) {
        return;
    }

    // 过滤非关注用户的推文
    const userIdStr = get(tweet, "raw.result.legacy.userIdStr");
    const isFollowing = restIds.includes(userIdStr);
    if (!isFollowing) {
        return;
    }

    const createdAt = get(tweet, "raw.result.legacy.createdAt");
    // return if more than 1 days
    if (dayjs().diff(dayjs(createdAt), "day") > 1) {
        return;
    }
    const publishTime = formatDateToLocalISO(createdAt);
    const screenName = get(tweet, "user.legacy.screenName");
    const tweetUrl = `https://x.com/${screenName}/status/${get(
        tweet,
        "raw.result.legacy.idStr"
    )}`;
    // 提取用户信息
    const user = {
        screenName: get(tweet, "user.legacy.screenName"),
        name: get(tweet, "user.legacy.name"),
    };

    // 提取图片
    const mediaItems = get(tweet, "raw.result.legacy.extendedEntities.media", []);
    const images = mediaItems
        .filter((media: any) => media.type === "photo")
        .map((media: any) => media.mediaUrlHttps);

    // 提取视频
    const videos = mediaItems
        .filter(
            (media: any) => media.type === "video" || media.type === "animated_gif"
        )
        .map((media: any) => {
            const variants = get(media, "videoInfo.variants", []);
            const bestQuality = variants
                .filter((v: any) => v.contentType === "video/mp4")
                .sort((a: any, b: any) => (b.bitrate || 0) - (a.bitrate || 0))[0];
            return bestQuality?.url;
        })
        .filter(Boolean);

    // 提取扩展的url
    const urlItems = get(tweet, "raw.result.legacy.entities.urls", []);
    const expandUrls = urlItems
        .map((urls: any) => urls.expandedUrl);

    rows.push({
        // @ts-ignore
        user,
        images,
        videos,
        expandUrls,
        tweetUrl,
        fullText,
        publishTime,
    });
});
console.log(`⏳ 初步筛选出符合关注用户且最近1天的原创推文，共${rows.length}条`);

const path = require('path');
const outputPath = `../tweets/${dayjs().format("YYYY-MM")}/${dayjs().format("YYYY-MM-DD")}.json`;
const dirPath = path.dirname(outputPath);

console.log(`📂 检查输出目录是否存在：${dirPath}`);
if (!fs.existsSync(dirPath)) {
    console.log(`📂 目录不存在，创建目录：${dirPath}`);
    fs.mkdirSync(dirPath, {recursive: true});
}

let existingRows: TweetApiUtilsData[] = [];

// 如果文件存在，读取现有内容
if (fs.existsSync(outputPath)) {
    console.log(`📂 读取现有数据文件：${outputPath}`);
    existingRows = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    console.log(`📋 现有文件中共有${existingRows.length}条记录`);
}

console.log(`🔄 合并现有数据（${existingRows.length}条）与新增数据（${rows.length}条）...`);
const allRows = [...existingRows, ...rows];
console.log(`📈 去重前总数据量：${allRows.length}条`);

// 通过 tweetUrl 去重
const uniqueRows = Array.from(
    new Map(allRows.map(row => [row.tweetUrl, row])).values()
);
console.log(`♻️ 去重后剩余数据量：${uniqueRows.length}条`);

console.log("📊 按推文ID升序排序数据...");
const sortedRows = uniqueRows.sort((a, b) => {
    const urlA = new URL(a.tweetUrl);
    const urlB = new URL(b.tweetUrl);
    const idA = urlA.pathname.split('/').pop() || '';
    const idB = urlB.pathname.split('/').pop() || '';
    return idA.localeCompare(idB); // Twitter ID 本身就包含时间信息，可以直接比较
});

console.log(`💾 正在写入数据到文件：${outputPath}`);
fs.writeFileSync(
    outputPath,
    JSON.stringify(sortedRows, null, 2)
);
console.log(`🎉 数据写入完成，共保存${sortedRows.length}条推文数据`);

console.log(`----- ----- ----- ----- fetch-home-latest-timeline end ----- ----- ----- -----`);