# Telegram Drive

一个现代化的文件存储系统，使用 Telegram 作为后端存储提供商。

## 🌟 特性

- 📁 **文件管理**: 上传、下载、移动、重命名、删除文件
- 🗂️ **目录结构**: 分层文件夹组织
- 🔄 **去重处理**: 基于校验和的自动文件去重
- 🗑️ **软删除**: 回收站功能
- 📦 **大文件支持**: 通过 Telegram 处理最大 2GB 的文件
- 🔐 **安全**: 加密会话存储，可选 API 令牌认证
- 🌐 **现代 Web UI**: 响应式前端界面
- 🚀 **高性能**: 异步处理，连接池，流式传输

## 🏗️ 项目结构

```
telegram-drive/
├── backend/          # FastAPI 后端服务
│   ├── app/          # 应用代码（整洁架构）
│   ├── alembic/      # 数据库迁移
│   └── run.py        # 启动脚本
├── frontend/         # Vue.js 前端应用
│   ├── src/          # 源代码
│   └── dist/         # 构建输出
└── README.md         # 项目文档
```

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 12+
- Telegram Bot Token（从 @BotFather 获取）
- Telegram API 凭据（api_id, api_hash）

### 1. 克隆项目

```bash
git clone https://github.com/1653756334/telegram-drive
cd telegram-drive
```

### 2. 后端设置

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置你的设置

# 运行数据库迁移
alembic upgrade head

# 启动后端服务
python run.py
```

后端服务将在 http://localhost:8000 启动

### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端应用将在 http://localhost:5173 启动

## 📚 文档

- [后端文档](./backend/README.md) - 详细的后端架构和 API 文档

## 🔧 配置

主要环境变量：

```env
# Telegram API
TGDRIVE_API_ID=your_api_id
TGDRIVE_API_HASH=your_api_hash
TGDRIVE_BOT_TOKEN=your_bot_token

# 数据库
TGDRIVE_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# 存储频道
TGDRIVE_STORAGE_CHANNEL_USERNAME=@your_channel
```

详细配置请参考 [后端文档](./backend/README.md)。

## 🏛️ 架构

项目采用现代化的架构设计：

- **后端**: 整洁架构 + 领域驱动设计 (DDD)
- **前端**: 组件化架构 + 响应式设计
- **数据库**: PostgreSQL 关系数据库
- **存储**: Telegram 作为文件存储后端

## 🙏 致谢

- [Telegram](https://telegram.org/) - 提供强大的 API 和存储能力
- [FastAPI](https://fastapi.tiangolo.com/) - 优秀的 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
