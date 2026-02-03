# 如何寻找和测试免费 API

当公共的聚合 API（如 `vvhan`, `tenapi`, `oioweb`）不稳定时，你可以通过以下方法找到新的 API，或者直接使用官方接口。

## 方法一：使用 API 聚合平台搜索

很多开发者维护了 API 列表，你可以在 Google 或 GitHub 搜索：
- 关键词：`微博热搜 API 2025`、`知乎热榜 JSON API`、`免费 API 接口`
- 常用聚合站：
    - **搏天 API**: `https://api.btstu.cn`
    - **韩小韩 API**: `https://api.vvhan.com` (你刚才试过，不稳定)
    - **Uomg API**: `https://api.uomg.com`
    - **夏柔 API**: `https://api.aa1.cn`

**测试方法**：
找到一个 URL（例如 `https://api.aa1.cn/api/weibo-hot`），复制到浏览器地址栏打开。
- 如果看到一大串 JSON 数据（类似 `{"code": 200, "data": [...]}`），说明 API 可用。
- 如果网页打不开或报错，说明不可用。

---

## 方法二：浏览器“抓包”官方接口（最稳定）

这是获取数据最直接的方法，直接找官方 App 或网页调用的接口。

### 以【微博热搜】为例：

1. 打开浏览器（Chrome/Edge），按 `F12` 打开开发者工具。
2. 切换到 **Network (网络)** 标签页。
3. 选择 **Fetch/XHR** 过滤器（只看数据请求）。
4. 访问 [微博热修网页版](https://s.weibo.com/top/summary) 或个人主页。
5. 观察加载出来的请求。
    - 你会发现一个叫 `summary` 或者 `hot_band` 的请求。
    - 右键该请求 -> **Open in new tab**。
    - 如果能看到数据，复制这个 URL。
    - **注意**：有些官方接口需要 Cookie 才能访问（即你在浏览器能开，代码里报错 403）。这种情况需要更复杂的配置（添加 Headers），或者找那种不需要登录的接口。

**当前已知的官方公开接口（无需登录）**：
- 微博：`https://weibo.com/ajax/statuses/hot_band`
- 知乎：`https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total`

如果这些在代码里报错（403/401），说明官方加了反爬虫限制（校验 User-Agent 或 Referer）。

---

## 方法三：快速验证代码

你可以在项目目录下新建一个 `test_api.py`，把找到的 URL 填进去测试：

```python
import requests

# 把你找到的 URL 填在这里
URL = "https://tenapi.cn/v2/weibohot"

try:
    resp = requests.get(URL, timeout=5)
    print("状态码:", resp.status_code)
    print("返回内容前100字:", resp.text[:100])
except Exception as e:
    print("请求失败:", e)
```

运行 `python test_api.py`，如果状态码是 200 且有内容，就可以用到项目中。

---

## 下一步建议

既然公共 API 不稳定，我建议你在 `config.py` 中把 API 地址变成**可配置项**。这样你找到新的 API 后，只需要改配置，不用动代码。

我现在会帮你把项目结构优化一下。
