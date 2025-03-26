# Discuz论坛自动签到工具

这是一个基于GitHub Actions的Discuz论坛自动签到工具，支持验证码识别、每日签到和随机访问用户主页以提高账号活跃度。

## 功能特点

- 全自动登录，支持验证码识别
- 自动每日签到获取积分/金币
- 随机访问用户主页提高账号活跃度
- 使用GitHub Actions，无需服务器
- 每天北京时间0点定时执行

## 使用方法

### 快速开始

1. Fork本仓库到你的GitHub账号

2. 在你的仓库中设置以下Secrets（Settings > Secrets and variables > Actions）:
   - `HOSTNAME`: 论坛域名 (例如: `www.xxx.com`)
   - `USERNAME`: 你的论坛用户名
   - `PASSWORD`: 你的论坛密码

3. 启用GitHub Actions (如果尚未启用)

4. 完成！GitHub Actions将按计划自动运行 (每天北京时间0点)，也可以手动触发工作流

### 手动运行

在GitHub仓库页面点击"Actions"选项卡，选择"每日签到"工作流，然后点击"Run workflow"按钮手动触发运行。

## 工作原理

该工具使用Python脚本完成以下任务:

1. **自动登录**：使用账号密码登录论坛，自动识别和处理验证码
2. **签到**：访问论坛签到页面执行签到操作
3. **活跃度提升**：随机访问多个用户主页，增加账号活跃度

整个过程通过GitHub Actions自动运行，不需要维护自己的服务器。

- 请勿滥用
- 所有敏感信息（如用户名密码）均存储在GitHub Secrets中，不会泄露
- 如果论坛更改了签到机制，可能需要更新脚本

## 结构

- `discuz.py`: 主程序，包含签到和访问用户页面的逻辑
- `login.py`: 处理登录、验证码识别等功能
- `requirements.txt`: 依赖包列表
- `.github/workflows/daily-signin.yml`: GitHub Actions工作流配置文件




## 常见问题

### 签到失败

问题：日志显示"签到失败"
解决方法：
- 检查账号密码是否正确
- 确认论坛域名是否填写正确（不要包含http://或https://）
- 查看Actions日志了解详细错误信息

### 验证码识别失败

问题：频繁提示"验证码识别失败"
解决方法：
- 验证码识别模块有一定错误率，脚本会自动重试
- 如果持续失败，可能是论坛验证码类型发生变化，需要更新脚本

### 执行时间不准确

问题：脚本没有在预期时间执行
解决方法：
- GitHub Actions的定时任务执行时间可能有延迟，这是正常现象
- 确保cron表达式设置正确（注意UTC时间与本地时间的转换）

## 相关项目

- [ddddocr](https://github.com/sml2h3/ddddocr): 本项目使用的验证码识别库
- [cloudscraper](https://github.com/venomous/cloudscraper): 用于绕过Cloudflare保护

## 免责声明

本工具仅供学习交流使用，请遵守论坛规则和相关法律法规。使用本工具造成的任何问题，作者概不负责。请勿将本工具用于商业或非法用途。
