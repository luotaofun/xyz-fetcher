# 小宇宙播客爬虫


## 功能

- 抓取指定播客的信息

- 抓取指定播客的节目列表

- 抓取指定节目信息

- 抓取指定节目的逐字稿

- 抓取指定节目的所有评论

- 使用 MongoDB 存储抓取数据

## 配置

创建并激活 venv 环境

``` Bash
python -m venv .venv

# On unix like OS
source .venv/bin/activate

# On Windows (PowerShell)
& .venv/Scripts/Activate.ps1
```

安装依赖

``` Bash
pip install -r requirements.txt
```

创建配置文件 `data/config.toml`（示例）

``` Toml
[fetcher]
token_filename = 'token.json'
device_idfv = '<x-jike-device-properties::idfv>'
device_id = '<x-jike-device-id>'

[database]
host = '127.0.0.1'
port = 27017

username = '<MongoDB Username>'
password = '<MongoDB Password>'
database_name = 'xyz-data'
```

创建 token 文件 `data/token.json`（示例）

``` JSON
{
    "access_token": "<x-jike-access-token>",
    "refresh_token": "<x-jike-refresh-token>"
}
```

## 运行

### 抓取节目信息及其评论

``` Bash
python src/main.py --eid=<episode_id>
```

### 抓取播客的所有节目

``` Bash
python src/main.py --pid=<podcast_id>
```

默认同时抓取每个节目的评论和逐字稿；加 `--no-fetch-comments` 可只抓节目，加 `--no-fetch-transcripts` 可跳过逐字稿。
使用 `--episodes-max-count=<n>` 限制抓取期数（0 为全部，注意按整页生效，每页最多 20 条）。


``` Toml
[mysql]
host = '127.0.0.1'
port = 3306

user = '<MySQL Username>'
password = '<MySQL Password>'
database_name = ''
```

### 查看所有选项

``` Bash
python src/main.py --help
```

## License

[MIT License](license)
