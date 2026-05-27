# 信息雷达

一个手机优先的信息雷达，自动抓取并整理：

- TikTok Creative Center 热门话题
- GitHub 近 14 天快速涨星的 AI 项目
- 国内财经相关新闻

## 本地运行

```powershell
python server.py
```

然后打开：

```text
http://127.0.0.1:4174
```

同一 Wi-Fi 下的手机可以打开电脑局域网 IP，例如：

```text
http://你的电脑IP:4174
```

## 部署到 Render

1. 在 GitHub 新建一个仓库，例如 `signal-radar`。
2. 把本项目文件上传到仓库。
3. 打开 Render，选择 `New Web Service`。
4. 连接这个 GitHub 仓库。
5. Render 会读取 `render.yaml`，使用 `python server.py` 启动。
6. 部署完成后会得到一个公网地址，例如：

```text
https://signal-radar.onrender.com
```

## 绑定免费子域名

可以用 is-a.dev 申请免费子域名。

1. Fork `is-a-dev/register`。
2. 在 `domains/` 目录新增 `你的名字.json`。
3. 指向 Render 给你的公网地址。
4. 提交 Pull Request，等待合并。

合并后就可以用类似下面的地址访问：

```text
https://你的名字.is-a.dev
```
