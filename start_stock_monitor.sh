

IS_SANDBOX=1 claude --dangerously-skip-permissions docker中启动yolo模式

# 启动监控（初始股票 300759 和 03759.HK，开启飞书）
python3 start_stock_monitor_v2.py \
    -s 03759.HK 300759 \
    --level3 0.2 \
    --level2 3.5 \
    --level1 3.5 \
    --window 10 \
    --interval 10 \
    --feishu-on \
    --notify-start

# 列出当前监控
python3 start_stock_monitor_v2.py --list

# 运行时添加股票
python3 start_stock_monitor_v2.py -s 6127.HK --add

# 运行时移除股票
python3 start_stock_monitor_v2.py -s 03759.HK --remove

# 切换飞书通知开关
python3 start_stock_monitor_v2.py --feishu-off
python3 start_stock_monitor_v2.py --feishu-on


python3 start_stock_monitor_v2.py -s 300759 03759.HK 300418 运行的时候，
1.不通过get_stock_name得到股票名称，而是通过平台库得到
2.测试运行，查看是否正常，是否能正常发送飞书通知监控股票涨跌幅，
3.自己测试发现无法正常发送飞书通知，控股票涨跌幅为0.1%

# 启动监控（300759、03759.HK、300418）
python3 start_stock_monitor_v2.py -s 300759 03759.HK 300418 --feishu-on --notify-start

# 自定义阈值（如 0.1% 测试）
python3 start_stock_monitor_v2.py -s 03759.HK  --level3 0.1 --feishu-on --notify-start

# 列出当前监控
python3 start_stock_monitor_v2.py --list