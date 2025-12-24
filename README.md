# EduMate - Personalized Learning Companion

一个基于 Flask 的个性化学习推荐系统，为大学生提供智能学习资源推荐和进度跟踪服务。

## 🌟 功能特性

### 核心功能
- **用户管理**：多角色认证系统（学生、教师、管理员）
- **内容管理**：学习资料上传、分类和管理
- **智能推荐**：基于规则的个性化内容推荐算法
- **反馈系统**：用户评分和评论，持续优化推荐质量
- **进度跟踪**：学习活动监控和成就统计
- **管理面板**：系统分析和内容管理

### 技术栈
- **后端**：Python 3.8+ / Flask 2.3.3
- **数据库**：SQLite 3.x（支持 MySQL 扩展）
- **前端**：HTML5 / CSS3 / JavaScript / Bootstrap 5
- **认证**：基于会话的认证，密码哈希加密
- **可视化**：Chart.js 数据分析图表
- **部署**：Gunicorn + Nginx（生产环境）

## 📁 项目结构

```
edumate/
├── app.py                      # Flask 主应用
├── config.py                   # 配置管理
├── requirements.txt            # Python 依赖
├── run.py                     # 应用启动脚本
├── .env.local                 # 环境变量（本地）
├── database/
│   └── sqlite_init.py         # SQLite 数据库初始化
├── routes/                    # Flask 路由模块
│   ├── __init__.py
│   ├── auth.py               # 认证路由
│   ├── user.py               # 用户管理
│   ├── content.py            # 内容管理
│   ├── recommendation.py     # 推荐系统
│   └── admin.py              # 管理面板
├── templates/                 # Jinja2 模板
│   ├── base.html             # 基础模板
│   ├── auth/                 # 认证页面
│   ├── user/                 # 用户页面
│   ├── content/              # 内容页面
│   ├── recommendation/       # 推荐页面
│   └── admin/               # 管理页面
├── static/                   # 静态资源
│   ├── css/
│   │   └── style.css        # 自定义样式
│   └── js/
│       └── main.js          # 主要 JavaScript
├── uploads/                  # 文件上传目录
├── nginx/                    # Nginx 配置
└── scripts/                  # 部署脚本
    └── deploy.sh            # Linux 部署脚本
```

## 🚀 Linux 部署指南

### 系统要求

#### 操作系统
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- 或其他主流 Linux 发行版

#### 软件依赖
- Python 3.8 或更高版本
- SQLite 3.x（默认）或 MySQL 5.7+
- Nginx 1.18+（生产环境）
- Git

### 1. 环境准备

#### 更新系统包
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

#### 安装必要软件
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv sqlite3 nginx git

# CentOS/RHEL
sudo yum install -y python3 python3-pip sqlite nginx git
```

### 2. 下载项目

```bash
# 克隆项目
git clone <repository-url>
cd edumate

# 设置目录权限
chmod +x scripts/*.sh
```

### 3. Python 环境配置

#### 创建虚拟环境
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

#### 安装依赖
```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

### 4. 数据库配置

#### SQLite 配置（推荐，简单快速）
```bash
# 初始化数据库
python database/sqlite_init.py

# 验证数据库创建
ls -la edumate_local.db
```

#### MySQL 配置（可选，生产环境推荐）
```bash
# 安装 MySQL（如果尚未安装）
sudo apt install -y mysql-server

# 创建数据库和用户
sudo mysql -u root -p << EOF
CREATE DATABASE edumate CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'edumate_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON edumate.* TO 'edumate_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
EOF
```

#### 配置环境变量
```bash
# 创建生产环境配置
cp .env.local .env

# 编辑配置文件
nano .env
```

环境变量配置示例：
```env
# 应用配置
FLASK_ENV=production
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
PORT=5000

# 数据库配置（SQLite）
DATABASE_PATH=/path/to/your/edumate_local.db

# 数据库配置（MySQL，可选）
# DATABASE_URL=mysql://edumate_user:your_secure_password@localhost/edumate

# 安全配置
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
PERMANENT_SESSION_LIFETIME=86400
```

### 5. 应用配置优化

#### 修改生产环境配置
```bash
# 编辑 config.py 或设置环境变量
export FLASK_ENV=production
```

#### 配置文件上传目录
```bash
# 创建上传目录
mkdir -p uploads
chmod 755 uploads

# 设置静态文件权限
chmod -R 755 static/
```

### 6. 测试应用运行

#### 开发环境测试
```bash
# 激活虚拟环境
source venv/bin/activate

# 启动开发服务器
python run.py

# 测试访问
curl http://localhost:5000
```

#### 生产环境测试
```bash
# 使用 Gunicorn 启动
gunicorn -w 4 -b 127.0.0.1:5000 app:app

# 检查进程
ps aux | grep gunicorn
```

### 7. Nginx 配置

#### 创建 Nginx 配置文件
```bash
sudo nano /etc/nginx/sites-available/edumate
```

Nginx 配置内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    # 重定向到 HTTPS（生产环境推荐）
    # return 301 https://$server_name$request_uri;

    # 客户端最大上传大小
    client_max_body_size 100M;

    # 静态文件
    location /static {
        alias /path/to/edumate/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件
    location /uploads {
        alias /path/to/edumate/uploads;
        expires 1y;
        add_header Cache-Control "public";
    }

    # 应用代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# HTTPS 配置（生产环境）
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 其他配置与 HTTP 相同...
    client_max_body_size 100M;
    
    location /static {
        alias /path/to/edumate/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /path/to/edumate/uploads;
        expires 1y;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### 启用站点配置
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/edumate /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 8. 系统服务配置

#### 创建 Systemd 服务文件
```bash
sudo nano /etc/systemd/system/edumate.service
```

服务配置内容：
```ini
[Unit]
Description=EduMate Web Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/edumate
Environment=PATH=/path/to/edumate/venv/bin
EnvironmentFile=/path/to/edumate/.env
ExecStart=/path/to/edumate/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 启动和启用服务
```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start edumate

# 设置开机自启
sudo systemctl enable edumate

# 检查状态
sudo systemctl status edumate
```

### 9. SSL 证书配置（可选但推荐）

#### 使用 Let's Encrypt 获取免费证书
```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取并安装证书
sudo certbot --nginx -d your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 10. 防火墙配置

#### UFW 防火墙（Ubuntu）
```bash
# 启用防火墙
sudo ufw enable

# 允许 HTTP 和 HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许 SSH（如果需要）
sudo ufw allow 22/tcp

# 检查状态
sudo ufw status
```

## 🔧 默认账户

数据库初始化后，可以使用以下账户登录：

### 管理员账户
- **用户名**：`admin@edumate.com`
- **密码**：`admin123`
- **角色**：管理员

### 测试教师账户
- **用户名**：`test_instructor`
- **密码**：`instructor123`
- **角色**：教师

### 测试学生账户
- **用户名**：`test_student`
- **密码**：`student123`
- **角色**：学生

**⚠️ 重要提示**：部署到生产环境后，请立即修改默认密码！

## 📋 用户角色权限

### 学生 (Student)
- 浏览和搜索学习内容
- 查看个性化推荐
- 跟踪学习进度
- 对内容评分和评论
- 管理个人资料和偏好设置

### 教师 (Instructor)
- 拥有学生的所有权限
- 上传和管理学习材料
- 查看内容分析数据
- 管理内容分类

### 管理员 (Administrator)
- 拥有教师的所有权限
- 管理用户账户（激活/停用）
- 系统分析和报告
- 内容审核和管理
- 系统配置管理

## 🗄️ 数据库架构

### 核心数据表
- `users` - 用户账户和资料信息
- `content` - 学习材料和资源
- `categories` - 内容分类管理
- `user_activities` - 学习进度跟踪
- `content_feedback` - 用户评分和评论
- `recommendations` - 推荐系统记录
- `user_preferences` - 个性化设置
- `system_logs` - 管理审计日志

## 🌐 API 端点

### 认证相关
- `POST /auth/login` - 用户登录
- `POST /auth/register` - 用户注册
- `GET /auth/logout` - 用户登出

### 内容管理
- `GET /content/browse` - 浏览内容（支持筛选）
- `GET /content/<id>` - 查看具体内容
- `POST /content/upload` - 上传新内容（教师/管理员）
- `POST /content/<id>/rate` - 内容评分
- `POST /content/<id>/activity` - 记录学习活动

### 推荐系统
- `GET /recommendation/for-you` - 个性化推荐
- `GET /recommendation/trending` - 热门内容
- `GET /recommendation/api/refresh` - 刷新推荐

### 管理功能
- `GET /admin/dashboard` - 管理仪表板
- `GET /admin/users` - 用户管理
- `GET /admin/content` - 内容管理
- `GET /admin/analytics` - 系统分析

## 🤖 推荐算法

系统采用基于规则的推荐方法，综合考虑：
- 用户兴趣和偏好设置
- 内容难度等级匹配
- 用户学习历史记录
- 内容受欢迎程度和评分
- 分类偏好分析

## 🔒 安全特性

- 使用 Werkzeug 进行密码哈希加密
- 基于会话的用户认证机制
- 输入验证和数据清理
- SQL 注入攻击防护
- 跨站脚本攻击 (XSS) 防护
- 基于角色的访问控制 (RBAC)
- 安全的会话管理

## ⚡ 性能优化

- 数据库查询优化和索引
- 大数据集的懒加载机制
- 常用数据缓存策略
- 移动设备响应式设计
- 静态资源优化交付
- Gzip 压缩支持

## 🛠️ 开发规范

### 代码风格
- 遵循 PEP 8 Python 编码规范
- 使用描述性变量命名
- 为函数添加文档字符串
- 实施适当的错误处理

### 数据库规范
- 使用参数化查询防止 SQL 注入
- 实施适当的外键约束
- 包含时间戳用于追踪
- 适当的数据规范化

### 前端规范
- 移动优先的响应式设计
- 渐进式增强策略
- 可访问的 HTML 标记
- 一致的 UI 组件设计

## 🧪 测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试（如果有测试文件）
python -m pytest tests/

# 或运行基本功能测试
python -c "
import app
print('✅ Application imports successfully')
"
```

## 📊 监控和日志

### 应用日志
```bash
# 查看应用日志
sudo journalctl -u edumate -f

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 系统监控
```bash
# 检查服务状态
sudo systemctl status edumate
sudo systemctl status nginx

# 检查端口监听
sudo netstat -tlnp | grep :5000
sudo netstat -tlnp | grep :80
```

## 🔧 维护和更新

### 备份数据库
```bash
# SQLite 备份
cp edumate_local.db backup/edumate_$(date +%Y%m%d_%H%M%S).db

# MySQL 备份（如果使用 MySQL）
mysqldump -u edumate_user -p edumate > backup/edumate_$(date +%Y%m%d_%H%M%S).sql
```

### 更新应用
```bash
# 停止服务
sudo systemctl stop edumate

# 拉取最新代码
git pull origin main

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl start edumate
```

## 🐛 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la edumate_local.db

# 检查数据库路径配置
grep DATABASE_PATH .env
```

#### 2. 静态文件 404
```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查文件权限
ls -la static/
```

#### 3. 上传文件失败
```bash
# 检查上传目录权限
ls -la uploads/

# 设置正确权限
chmod 755 uploads/
chown www-data:www-data uploads/
```

#### 4. 服务启动失败
```bash
# 查看详细错误信息
sudo journalctl -u edumate -n 50

# 检查配置文件
sudo nano /etc/systemd/system/edumate.service
```

## 📈 性能调优

### Gunicorn 配置优化
```bash
# 根据服务器配置调整 worker 数量
# 通常建议：(2 * CPU核心数) + 1
gunicorn -w 4 -b 127.0.0.1:5000 app:app

# 添加超时和worker类型
gunicorn -w 4 -k gevent --worker-connections 1000 -t 60 -b 127.0.0.1:5000 app:app
```

### Nginx 缓存配置
```nginx
# 在 location 块中添加缓存配置
location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 🤝 贡献指南

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如需支持和帮助：

- 📋 在仓库中创建 Issue
- 📧 联系开发团队
- 📖 查看项目文档
- 🐛 报告 Bug 或功能请求

## 🙏 致谢

本项目为马来西亚理科大学 CAT304W 团队创新项目开发，符合联合国可持续发展目标 4：优质教育。

---

**🎓 EduMate - 让学习更智能，让教育更个性化**

如果这个项目对你有帮助，请给我们一个 ⭐ Star！