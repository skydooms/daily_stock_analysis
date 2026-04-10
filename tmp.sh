IS_SANDBOX=1 claude --dangerously-skip-permissions docker中启动yolo模式


python webui.py
WEBUI_HOST=0.0.0.0 WEBUI_PORT=8000 python3 webui.py
python main.py 

配置该工程的相关环境，完成后运行调试python3 main.py --webui --market-review
tavily  sky: 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






  python3 start_stock_monitor.py --help       # 查看帮助                                                                                                
  python3 start_stock_monitor.py --list --notify-start      # 列出监控                                                                                                
  python3 start_stock_monitor.py -s 300759    # 添加监控                                                                                                
  python3 start_stock_monitor.py -s 300759 --remove  # 移除监控                                                                                         
  python3 start_stock_monitor.py -s 600519 --force   # 强制替换  


  python3 start_stock_monitor.py -s 300759 03759.HK  --force --notify-start  # 移除监控并发送飞书通知


git config --global user.email "sky@example.com"
git config --global user.name "sky"

# 配置邮箱（必须是你 GitHub 注册的邮箱）
git config --global user.email "yonggedage@163.com"
# 配置用户名（你的GitHub用户名/真实名字都可以）
git config --global user.name "skydooms"