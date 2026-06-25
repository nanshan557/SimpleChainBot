# Simple Chain 每日签到机器人 

[Simple Chain](https://task.simplechain.com?inviteCode=9v6nkso475f) 自动化每日任务机器人。

每隔 24 小时自动运行 —— 完成钱包登录、访问任务和每日签到。

---

## 功能

- ✅ 每日签到
- ✅ 访问任务
- ✅ 自动每 24 小时循环执行
- ✅ 支持多钱包
- ✅ 可选代理支持

---

## 环境要求

- Python 3.8+
- pip 包（见 `requirements.txt`）

---

## 安装与配置

### 1. 克隆仓库

```bash
git clone https://github.com/nanshan557/SimpleChainBot.git
cd SimpleChainBot
```



### 2. 配置私钥和代理

在 `keys.example.txt` 和 `proxy.example.txt` 中配置你的私钥和代理信息，**每行一个**。

#### `keys.example.txt` — 私钥文件（必填）

每行一个以太坊私钥：

```text
0x你的私钥1
0x你的私钥2
```



> ⚠️ **切勿分享你的私钥！务必妥善保管！**

#### `proxy.example.txt` — 代理文件（可选）

每行一个代理，支持以下格式：

```text
http://用户名:密码@主机:端口
socks5://用户名:密码@主机:端口
IP:端口
```



> 如果不需要代理，请将该文件留空或直接省略。

------

## 运行方法

### 方式一：一键运行（推荐）

**Windows：**

```bash
run.bat
```



**Linux：**

```bash
run.sh
```



### 方式二：手动安装运行

**Linux / macOS：**

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp keys.example.txt keys.txt      # 配置私钥（必填）
cp proxy.example.txt proxy.txt    # 配置代理（可选）
python main.py
```



**Windows：**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy keys.example.txt keys.txt     # 配置私钥（必填）
copy proxy.example.txt proxy.txt   # 配置代理（可选）
python main.py
```



------

## 文件结构

```text
SimpleChainBot/
├── main.py               # 主程序
├── keys.txt              # 私钥文件（需自行配置）
├── proxy.txt             # 代理文件（需自行配置，可选）
├── keys.example.txt      # 私钥示例文件
├── proxy.example.txt     # 代理示例文件
├── requirements.txt      # 依赖列表
├── run.bat               # Windows 一键启动脚本
├── run.sh                # Linux 一键启动脚本
└── README.md
```



------

## 免责声明

本机器人仅供**教育用途**。使用风险自负，作者不对任何**资金损失**或**账户封禁**负责。请务必妥善保管你的私钥。

------

## 许可证

MIT License