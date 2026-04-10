1.出一个工程的文档，包括工程的目录结构，每个文件的功能，以及每个函数的参数和返回值。
2.工程的每个功能进行详细的说明，包括功能的实现原理，以及功能的使用方法。

    
git config --global http.proxy http://127.0.0.1:1087
git config --global https.proxy http://127.0.0.1:1087


# 晨间复盘（7:00）
python3 main.py --morning-review

# 午间监测（12:00）
python3 main.py --noon-monitor

# 晚间监测（19:00）
docker exec -it claude_code bash 
python3 main.py --evening-monitor
python3 main.py --morning-review
# 多时间点调度模式
python3 main.py --multi-schedule
                         

# 晨间复盘
docker exec claude_code bash -c "cd /home/sky/project/daily_stock_analysis && python3 main.py --morning-review"

# 午间监测  
docker exec claude_code bash -c "cd /home/sky/project/daily_stock_analysis && python3 main.py --noon-monitor"

# 晚间监测
docker exec claude_code bash -c "cd /home/sky/project/daily_stock_analysis && python3 main.py --evening-monitor"