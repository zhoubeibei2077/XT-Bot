import {TwitterOpenApi} from "twitter-openapi-typescript";
import axios from "axios";
import {TwitterApi} from 'twitter-api-v2';

export const _xClient = async (TOKEN: string) => {
    // console.log("🚀 ~ const_xClient= ~ TOKEN:", TOKEN)
    const resp = await axios.get("https://x.com/manifest.json", {
        headers: {
            cookie: `auth_token=${TOKEN}`,
        },
    });

    const resCookie = resp.headers["set-cookie"] as string[];
    const cookieObj = resCookie.reduce((acc: Record<string, string>, cookie: string) => {
        const [name, value] = cookie.split(";")[0].split("=");
        acc[name] = value;
        return acc;
    }, {});

    // console.log("🚀 ~ cookieObj ~ cookieObj:", JSON.stringify(cookieObj, null, 2))

    const api = new TwitterOpenApi();
    const client = await api.getClientFromCookies({...cookieObj, auth_token: TOKEN});
    if (!client) {
        throw new Error('客户端未初始化');
    }
    console.log('🔑 认证客户端已创建');
    return client;
};

export const XAuthClient = () => _xClient(process.env.AUTH_TOKEN!);

