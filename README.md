# Haier

本插件可将海尔智家中的设备接入HomeAssistant，理论上支持所有设备。

本仓库基于 [`banto6/haier`](https://github.com/banto6/haier) 开发，增加海尔智家 App
账号密码直登、令牌自动续期和 Home Assistant 重新认证流程。首次配置不需要抓包或手工填写
`client_id` / `refresh_token`；密码仅用于向海尔登录接口换取令牌，不会写入 Home Assistant
配置。

> [!NOTE]
> 提交问题时请按Issues模版填写，未按模板填写问题会被忽略和关闭!!!

## 已支持实体
- Switch
- Number
- Select
- Sensor
- Binary Sensor
- Climate

## 安装

方法1：下载并复制`custom_components/haier`文件夹到HomeAssistant根目录下的`custom_components`文件夹即可完成安装

方法2：已经安装了HACS，可以点击按钮快速安装 [![通过HACS添加集成](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wangty163&repository=haier&category=integration)

## 配置

配置 > 设备与服务 >  集成 >  添加集成 > 搜索`haier`

或者点击: [![添加集成](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=haier)

输入海尔智家 App 使用的账号和密码即可。登录成功后集成只保存 `client_id`、访问令牌和刷新令牌；
令牌失效且无法刷新时，Home Assistant 会显示重新认证流程。

## 常见问题

遇到问题请在 [wangty163/haier issues](https://github.com/wangty163/haier/issues) 中提交。


## 调试
在`configuration.yaml`中加入以下配置来打开调试日志。

```yaml
logger:
  default: warn
  logs:
    custom_components.haier: debug
```
