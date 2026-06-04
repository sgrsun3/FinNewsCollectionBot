# 福生无量天尊
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
    print("⚠️ openai 模块不可用，DeepSeek 相关功能将被禁用。若需要，请安装 openai 包并设置 OPENAI_API_KEY。")
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import os
import re
import traceback

# OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")

# 从环境变量获取 Server酱 SendKeys（非必须，未设置时仅打印摘要）
server_chan_keys_env = os.getenv("SERVER_CHAN_KEYS", "")
if server_chan_keys_env and server_chan_keys_env.strip():
    server_chan_keys = [k.strip() for k in server_chan_keys_env.split(",") if k.strip()]
else:
    server_chan_keys = []
    print("⚠️ 环境变量 SERVER_CHAN_KEYS 未设置，推送功能将被禁用。设置 SERVER_CHAN_KEYS 后可启用微信推送。")

# 初始化 OpenAI/DeepSeek 客户端（可选）
openai_client = None
if openai_api_key:
    try:
        openai_client = OpenAI(api_key=openai_api_key, base_url="https://api.deepseek.com/v1")
    except Exception as e:
        print(f"⚠️ 无法初始化 OpenAI/DeepSeek 客户端: {e}")

# 是否启用 DeepSeek 语义分类（以客户端是否可用为准）
USE_DEEPSEEK = bool(openai_client)

# RSS源地址列表
rss_feeds = {
    "💲 财经媒体": {
        "华尔街见闻": "https://dedicated.wallstreetcn.com/rss.xml",
        "东方财富": "http://rss.eastmoney.com/rss_partener.xml",
        "财联社": "https://www.cls.cn/rss",
        "第一财经": "https://www.yicai.com/rss/rss.xml",
        "每日经济新闻": "https://www.nbd.com.cn/rss",
        "财经网": "https://www.caijing.com.cn/rss/index.xml",
        "证券时报": "https://www.stcn.com/rss/",
        "界面新闻": "https://www.jiemian.com/feed",
        "香港经济日报": "https://www.hket.com/rss/china",
        "中新网财经": "https://www.chinanews.com.cn/rss/finance.xml",
        "人民日报财经": "http://www.people.com.cn/rss/finance.xml",
    },
    "💻 科技媒体": {
        "36氪": "https://36kr.com/feed",
        "虎嗅网": "https://www.huxiu.com/rss/0.xml",
        "钛媒体": "https://www.tmtpost.com/rss",
        "爱范儿": "https://www.ifanr.com/feed",
        "PingWest品玩": "https://www.pingwest.com/feed",
        "新浪科技": "https://tech.sina.com.cn/rss/tech.xml",
        "网易科技": "https://tech.163.com/special/000915JB/rss_tech.xml",
        "腾讯科技": "https://tech.qq.com/rss/tech.xml",
        "极客公园": "https://www.geekpark.net/rss",
        "IT之家": "https://www.ithome.com/rss/",
        "cnBeta": "https://www.cnbeta.com/backend.php",
        "Engadget中文": "https://cn.engadget.com/rss.xml",
    },
    "🛒 零售与电商": {
        "亿欧": "https://www.iyiou.com/rss",
        "联商网": "https://www.linkshop.com.cn/rss",
        "零售老板内参": "https://www.lslb.com/feed",
        "电商报": "https://www.dsb.cn/feed",
        "天下网商": "https://www.wshang.com/rss",
    },
    "📱 社交与内容": {
        "新榜": "https://www.newrank.cn/feed",
        "微果酱": "https://www.wogame.com/feed",
        "广告门": "https://www.adquan.com/rss",
        "知乎每日精选": "https://www.zhihu.com/rss",
    },
    "📰 综合新闻": {
        "今日头条": "https://toutiao.com/rss",
        "澎湃新闻": "https://www.thepaper.cn/rss",
        "封面新闻": "https://www.thecover.cn/rss",
        "人民日报时政": "http://www.people.com.cn/rss/politics.xml",
        "人民日报国际": "http://www.people.com.cn/rss/world.xml",
    },
    "🇺🇸 国际财经": {
        "华尔街日报": "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
        "MarketWatch": "https://www.marketwatch.com/rss/topstories",
        "BBC商业": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "CNBC财经": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "CNBC商业": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "CNBC投资": "https://www.cnbc.com/id/15839069/device/rss/rss.html",
        "CNBC财报": "https://www.cnbc.com/id/15839135/device/rss/rss.html",
        "CNBC新闻": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    },
    "📈 A股市场": {
        "个股频道": "http://rss.jrj.com.cn/stock/725.xml",
        "综合频道": "http://rss.jrj.com.cn/stock/734.xml",
        "个股异动": "http://rss.jrj.com.cn/stock/677.xml",
        "报刊头条": "http://rss.jrj.com.cn/stock/742.xml",
        "新股要闻": "http://rss.jrj.com.cn/stock/724.xml",
        "公告速递": "http://rss.jrj.com.cn/stock/729.xml",
        "今日提示": "http://rss.jrj.com.cn/stock/727.xml",
        "行业新闻": "http://rss.jrj.com.cn/stock/740.xml",
        "数据掘金": "http://rss.jrj.com.cn/stock/736.xml",
        "融资融券": "http://rss.jrj.com.cn/stock/733.xml",
        "机会情报": "http://rss.jrj.com.cn/stock/745.xml",
    },
    "🌍 港股市场": {
        "港交所参与者通告": "https://sc.hkex.com.hk/TuniS/www.hkex.com.hk/Services/RSS-Feeds/The-Stock-Exchange-of-Hong-Kong-Limited?sc_lang=zh-HK",
        "港交所研究资料": "https://sc.hkex.com.hk/TuniS/www.hkex.com.hk/Services/RSS-Feeds/Research-Materials?sc_lang=zh-HK",
    },
    "🇺🇸 美股市场": {
        "SeekingAlpha ETF策略": "https://seekingalpha.com/tag/etf-portfolio-strategy.xml",
        "SeekingAlpha IPO分析": "https://seekingalpha.com/tag/ipo-analysis.xml",
        "SeekingAlpha医疗板块": "https://seekingalpha.com/sector/healthcare.xml",
        "SeekingAlpha突发新闻": "https://seekingalpha.com/market_currents.xml",
        "纳斯达克财报": "https://www.nasdaq.com/feed/rssoutbound?category=Earnings",
        "纳斯达克市场": "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
        "纳斯达克分红": "https://www.nasdaq.com/feed/rssoutbound?category=Dividends",
        "SEC文件": "https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
    },
}

# 关键词过滤（中文 + 英文），可按需扩展
FILTER_KEYWORDS = [
    "零食", "零售", "连锁",
    "snack", "snacks", "retail", "chain", "chains",
    "convenience", "convenience store", "grocery", "supermarket",
    "store", "retailer"
]

def contains_keyword(text: str) -> bool:
    """快速关键词匹配（中/英混合）。"""
    if not text:
        return False
    text_lower = text.lower()
    for kw in FILTER_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def classify_titles_with_deepseek(titles: list) -> dict:
    """
    对一组新闻标题进行批量判定，返回编号到标签的映射。
    标签为 'YES'/'NO'/'MAYBE'。如果 DeepSeek 不可用，则基于关键词做保守回退（命中关键词为 YES，其他为 MAYBE）。
    """
    labels = {}
    if not titles:
        return labels

    # 初始化默认为 MAYBE（不剔除）
    for i in range(1, len(titles) + 1):
        labels[i] = 'MAYBE'

    if not USE_DEEPSEEK or not openai_client:
        for i, t in enumerate(titles, start=1):
            labels[i] = 'YES' if contains_keyword(t) else 'MAYBE'
        return labels

    # 构造编号标题列表
    numbered = "\n".join([f"{i}. {titles[i-1]}" for i in range(1, len(titles)+1)])
    system_prompt = (
        "你是一个简洁的三分类文本判断器。给定编号的新闻标题列表，判断每条标题是否与零食、零售、连锁相关（包括英文关键词 snack/retail/chain 等）。\n"
        "对于每个编号仅输出一行，格式为：编号: YES|NO|MAYBE。YES 表示明确相关，NO 表示明确不相关，MAYBE 表示仅凭标题无法判断。不要输出额外说明。"
    )
    try:
        resp = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": numbered}
            ],
            max_tokens=max(64, len(titles) * 6),
            temperature=0
        )
        text = resp.choices[0].message.content
        # 解析每行结果
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^\s*(\d+)\s*[:\.\)\-]?\s*([A-Za-z]+)", line, re.IGNORECASE)
            if m:
                idx = int(m.group(1))
                tag = m.group(2).upper()
                if tag.startswith('Y'):
                    labels[idx] = 'YES'
                elif tag.startswith('N'):
                    labels[idx] = 'NO'
                else:
                    labels[idx] = 'MAYBE'
            else:
                # 如果没有数字开头，尝试解析类似 "1 YES" 或包含 YES/NO 的行
                m2 = re.search(r"(YES|NO|MAYBE)", line, re.IGNORECASE)
                midx = re.search(r"^(\d+)", line)
                if midx and m2:
                    idx = int(midx.group(1))
                    tag = m2.group(1).upper()
                    labels[idx] = tag
        return labels
    except Exception as e:
        print(f"⚠️ 标题级 DeepSeek 判定出错：{e}，使用关键词回退")
        for i, t in enumerate(titles, start=1):
            labels[i] = 'YES' if contains_keyword(t) else 'MAYBE'
        return labels


def classify_text_with_deepseek(text: str) -> str:
    """
    对单篇文章（标题+正文）进行判定，返回 'YES'/'NO'/'MAYBE'。
    DeepSeek 不可用时基于关键词回退。出错时返回 'MAYBE'。
    """
    if not text:
        return 'MAYBE'
    if not USE_DEEPSEEK or not openai_client:
        return 'YES' if contains_keyword(text) else 'MAYBE'
    try:
        prompt_text = text[:3000]
        system_prompt = (
            "你是一个简洁的三分类文本判断器。判断给定新闻标题与正文是否与零食、零售、连锁相关（包括英文词如 snack, retail, chain 等）。\n"
            "只返回一个单词：YES 表示相关，NO 表示不相关，MAYBE 表示不确定或无法判断。不要额外说明。"
        )
        resp = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=6,
            temperature=0
        )
        out = resp.choices[0].message.content.strip().upper()
        if out.startswith('Y') or 'YES' in out:
            return 'YES'
        if out.startswith('N') or 'NO' in out:
            return 'NO'
        return 'MAYBE'
    except Exception as e:
        print(f"⚠️ 正文级 DeepSeek 判定出错：{e}")
        return 'MAYBE'

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()

# 爬取网页正文 (用于 AI 分析，但不展示)
def fetch_article_text(url):
    try:
        print(f"📰 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            print(f"⚠️ 文章内容为空: {url}")
        return text
    except Exception as e:
        print(f"❌ 文章爬取失败: {url}，错误: {e}")
        return "（未能获取文章正文）"

# 添加 User-Agent 头
def fetch_feed_with_headers(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)


# 自动重试获取 RSS
def fetch_feed_with_retry(url, retries=3, delay=5):
    for i in range(retries):
        try:
            feed = fetch_feed_with_headers(url)
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                return feed
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次请求 {url} 失败: {e}")
            time.sleep(delay)
    print(f"❌ 跳过 {url}, 尝试 {retries} 次后仍失败。")
    return None

# 获取RSS内容（爬取正文但不展示）
def fetch_rss_articles(rss_feeds, max_articles=None):
    news_data = {}
    analysis_text = ""  # 用于AI分析的正文内容

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, url in sources.items():
            print(f"📡 正在获取 {source} 的 RSS 源: {url}")
            feed = fetch_feed_with_retry(url)
            if not feed:
                print(f"⚠️ 无法获取 {source} 的 RSS 数据")
                continue
            print(f"✅ {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

            # 两轮筛选：1) 标题编号批量判定；2) 对保留项抓取正文并二次判定
            if max_articles:
                entries = feed.entries[:max_articles]
            else:
                entries = feed.entries
            titles = [e.get('title', '无标题') for e in entries]
            title_labels = classify_titles_with_deepseek(titles)
            # 打印所有判定结果
            label_strs = [f"{i}:{title_labels.get(i)}" for i in sorted(title_labels.keys())]
            # 如果结果太多，分块打印，每行最多10个
            for i in range(0, len(label_strs), 10):
                chunk = label_strs[i:i+10]
                if i == 0:
                    print(f"🔎 {source} 标题级判定: " + ", ".join(chunk))
                else:
                    print("   " + ", ".join(chunk))

            articles = []
            for idx, entry in enumerate(entries, start=1):
                title = entry.get('title', '无标题')
                link = entry.get('link', '') or entry.get('guid', '')
                summary = entry.get('summary', '') or entry.get('description', '') or ''
                if not link:
                    print(f"⚠️ {source} 的新闻 '{title}' 没有链接，跳过")
                    continue

                tlabel = title_labels.get(idx, 'MAYBE')
                if tlabel == 'NO':
                    print(f"⛔ 标题判定为非相关，跳过: [{idx}] {title}")
                    continue

                # 对保留项抓取正文并做二次判定
                article_text = fetch_article_text(link)
                check_text = f"{title}\n{article_text}"
                final_label = classify_text_with_deepseek(check_text)
                if final_label == 'NO':
                    print(f"⛔ 正文判定为非相关，移除: [{idx}] {title}")
                    continue

                # 保留（YES 或 MAYBE）
                analysis_text += f"【{title}】\n{article_text}\n\n"
                print(f"🔹 {source} - [{idx}] {title} 保留 (标题判定={tlabel} -> 正文判定={final_label})")
                articles.append(f"- [{title}]({link})")

            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"

        news_data[category] = category_content

    return news_data, analysis_text

# AI 生成内容摘要（基于爬取的正文）
def summarize(text):
    """
    使用 DeepSeek/OpenAI 生成摘要；若未配置 OpenAI，则回退为简单标题列表，且整体捕获异常保证脚本不崩溃。
    """
    try:
        if not USE_DEEPSEEK or not openai_client:
            # 回退：从 analysis_text 中提取标题列表
            titles = re.findall(r'【([^】]+)】', text)
            if not titles:
                return "（未配置 OPENAI_API_KEY，且未抓取到可分析的文章。）"
            return "未配置 OPENAI_API_KEY，以下为筛选后抓取到的相关文章标题：\n" + "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])

        completion = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": """
                 你是一名专业零食连锁零售行业的财经新闻分析师，请根据以下新闻内容，按照以下步骤完成任务：
                 1. 提取新闻中涉及的主要行业和主题，找出近1天涨幅最高的3个行业或主题，以及近3天涨幅较高且此前2周表现平淡的3个行业/主题。（如新闻未提供具体涨幅，请结合描述和市场情绪推测热点）
                 2. 针对每个热点，输出：
                    - 催化剂：分析近期上涨的可能原因（政策、数据、事件、情绪等）。
                    - 复盘：梳理过去3个月该行业/主题的核心逻辑、关键动态与阶段性走势。
                    - 展望：判断该热点是短期炒作还是有持续行情潜力。
                 3. 将以上分析整合为一篇1500字以内的财经热点摘要，逻辑清晰、重点突出，适合专业投资者阅读。
                 """},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ 生成摘要时出错：{e}")
        traceback.print_exc()
        # 回退到简单标题列表
        titles = re.findall(r'【([^】]+)】', text)
        if not titles:
            return "（生成摘要失败，且未抓取到可分析的文章。）"
        return "生成摘要失败，以下为筛选后抓取到的相关文章标题：\n" + "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])

# 发送微信推送
def send_to_wechat(title, content):
    for key in server_chan_keys:
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": title, "desp": content}
        response = requests.post(url, data=data, timeout=10)
        if response.ok:
            print(f"✅ 推送成功: {key}")
        else:
            print(f"❌ 推送失败: {key}, 响应：{response.text}")


if __name__ == "__main__":
    today_str = today_date().strftime("%Y-%m-%d")

    # 每个网站获取所有文章
    articles_data, analysis_text = fetch_rss_articles(rss_feeds)
    
    # AI生成摘要
    summary = summarize(analysis_text)

    # 生成仅展示标题和链接的最终消息
    final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\n{summary}\n\n---\n\n"
    for category, content in articles_data.items():
        if content.strip():
            final_summary += f"## {category}\n{content}\n\n"

    # 推送到多个server酱key
    send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)
