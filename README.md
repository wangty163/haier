# Haier

本插件可将海尔智家中的设备接入HomeAssistant，理论上支持所有设备。

本仓库基于 [`banto6/haier`](https://github.com/banto6/haier) 开发，增加海尔智家 App
账号密码直登、令牌自动续期和 Home Assistant 重新认证流程。首次配置不需要抓包或手工填写
`client_id` / `refresh_token`；密码仅用于向海尔登录接口换取令牌，不会写入 Home Assistant
配置。

> [!NOTE]
> 提交问题时请按Issues模版填写，未按模板填写问题会被忽略和关闭!!!

## 已支持实体

- Button
- Switch
- Number
- Select
- Time
- Sensor
- Binary Sensor
- Climate

## 已验证的官方 App 设备能力

- 卡萨帝 `CWC10-B29BKU1` 洗碗机：洗涤程序、启动/暂停、终止程序、预约、
  干燥、消毒、加强、漂洗、开机、远程授权、蜂鸣音开关、水软档位、光亮剂档位、
  启动/洗完/耗材/滤网/喷淋臂提醒、AI识水、热风烘干、峰谷电开关。
- 卡萨帝 `BCD-450WGCFDM4WNU1` 冰箱：冷藏室/冷冻室温度、婴爱空间、智能存储、
  速冻、外出节能、智慧动态净化、分时用电及谷段起止时间。

以上实体名称、程序选项和取值范围按对应型号当前官方 App 配置校准。商城、客服、
账户管理等非设备页面不创建 Home Assistant 实体。

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
