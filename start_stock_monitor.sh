

IS_SANDBOX=1 claude --dangerously-skip-permissions docker中启动yolo模式

python3 start_stock_monitor.py --help       # 查看帮助                                                                                                
python3 start_stock_monitor.py --list       # 列出监控                                                                                                
python3 start_stock_monitor.py -s 300759    # 添加监控                                                                                                
python3 start_stock_monitor.py -s 600519 --remove  # 移除监控                                                                                         
python3 start_stock_monitor.py -s 600519 --force   # 强制替换  