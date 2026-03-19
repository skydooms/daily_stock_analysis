IS_SANDBOX=1 claude --dangerously-skip-permissions docker中启动yolo模式



python main.py                    # 正常运行
python main.py --debug            # 调试模式
python main.py --dry-run          # 仅获取数据，不进行 AI 分析
python main.py --stocks 600519,000001  # 指定分析特定股票
python main.py --no-notify        # 不发送推送通知
python main.py --single-notify    # 启用单股推送模式（每分析完一只立即推送）
python main.py --schedule         # 启用定时任务模式
python main.py --market-review    # 仅运行大盘复盘

python webui.py
WEBUI_HOST=0.0.0.0 WEBUI_PORT=8000 python3 webui.py
python main.py 

配置该工程的相关环境，完成后运行调试python3 main.py --webui --market-review


tavily  sky: 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