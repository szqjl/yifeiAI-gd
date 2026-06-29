# GUA-097 Ablation Log — IP 规则对照批跑

> **设计目标**：每条 IP 规则上线前必须跑 baseline + 启用后批跑，机械化 V 系列"加规则不测"教训。
> **每行格式**：`date | mode | ip_id | description | win_rate | delta_vs_baseline | 备注`
> **联动**：每次跑通过 `scripts/hooks/post_batch_log.py` 写 `v7-win-rate-history.md`。

| date | mode | ip_id | description | win_rate | delta_vs_baseline | 备注 |
|------|------|-------|-------------|----------|-------------------|------|
