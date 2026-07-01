# 未发货仅退款客户挽回自动化 v1

本项目先实现“抓取结果处理、筛选、按月去重、写入钉钉跟进表”的闭环，暂不发送话术、不监控消息、不转接售前组。

## 当前能力

- 从钉钉店铺清单读取启用店铺，运行开关字段默认为 `是否`，值为 `是` 时启用。
- 解析淘宝/天猫后台导出的未发货仅退款订单文件，支持 `.xlsx`、`.csv`。
- 生成“前一日 00:00:00 至今日 23:59:59”的抓取时间窗。
- 按自然月 + 店铺名 + 旺旺ID 去重。
- 根据规则输出状态：
  - `待发送`
  - `跳过-今日已对话`
  - `跳过-当月重复`
  - `跳过-存在未完结订单`
  - `失败-异常原因`
- 自动创建月度钉钉跟进表，或复用配置里的已有跟进表。

## 快速开始

1. 复制配置：

```powershell
Copy-Item config.example.json config.local.json
```

2. 修改 `config.local.json`：

- `shop_list_node`：店铺清单钉钉表链接。
- `export_dir`：后台导出的退款订单文件目录。
- `monthly_report.folder`：月度跟进表要创建到的钉钉文件夹，可先留空。

3. 运行一次：

```powershell
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m refund_recovery.cli run --config config.local.json
```

4. 只解析本地导出文件、不写钉钉：

```powershell
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m refund_recovery.cli run --config config.local.json --dry-run
```

## 导出文件要求

导出文件名建议包含店铺名，例如：

```text
exports/旗舰店A_未发货仅退款_20260630.xlsx
```

字段支持常见别名：

- 订单号：`订单号`、`主订单编号`、`子订单编号`
- 旺旺ID：`旺旺ID`、`买家旺旺`、`买家昵称`
- 退款申请时间：`退款申请时间`、`申请时间`、`售后申请时间`
- 订单状态：`订单状态`、`交易状态`

如果导出文件没有旺旺ID，本版本会把该行标记为 `失败-异常原因`，原因是 `缺少旺旺ID`。

## 发送安全

`send_messages` 在配置和代码中都固定默认为 `false`。本版本不会发送任何话术，也不会执行千牛转接。
