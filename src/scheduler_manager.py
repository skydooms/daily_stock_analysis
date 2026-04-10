# -*- coding: utf-8 -*-
"""
===================================
多时间点调度管理器
===================================

职责：
1. 支持晨间复盘（7:00）、午间监测（12:00）、晚间监测（19:00）三个时间点
2. 管理多个调度任务的协调执行
3. 提供统一的任务注册和执行接口
"""

import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Callable, Dict, Optional, Any

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    优雅退出处理器
    
    捕获 SIGTERM/SIGINT 信号，确保任务完成后再退出
    """
    
    def __init__(self):
        self.shutdown_requested = False
        self._lock = threading.Lock()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        with self._lock:
            if not self.shutdown_requested:
                logger.info(f"收到退出信号 ({signum})，等待当前任务完成...")
                self.shutdown_requested = True
    
    @property
    def should_shutdown(self) -> bool:
        """检查是否应该退出"""
        with self._lock:
            return self.shutdown_requested


class ScheduledTask:
    """调度任务定义"""
    
    def __init__(
        self,
        name: str,
        schedule_time: str,
        task_func: Callable,
        enabled: bool = True,
        run_immediately: bool = False,
    ):
        self.name = name
        self.schedule_time = schedule_time
        self.task_func = task_func
        self.enabled = enabled
        self.run_immediately = run_immediately
        self.last_run: Optional[datetime] = None
        self.last_status: Optional[str] = None


class SchedulerManager:
    """
    多时间点调度管理器
    
    支持在多个固定时间点执行不同的任务：
    - 晨间复盘（7:00）
    - 午间监测（12:00）
    - 晚间监测（19:00）
    """
    
    DEFAULT_SCHEDULES = {
        'morning': '07:00',
        'noon': '12:00',
        'evening': '19:00',
    }
    
    def __init__(self):
        try:
            import schedule
            self.schedule = schedule
        except ImportError:
            logger.error("schedule 库未安装，请执行: pip install schedule")
            raise ImportError("请安装 schedule 库: pip install schedule")
        
        self.shutdown_handler = GracefulShutdown()
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
    
    def register_task(
        self,
        name: str,
        schedule_time: str,
        task_func: Callable,
        enabled: bool = True,
        run_immediately: bool = False,
    ) -> None:
        """
        注册调度任务
        
        Args:
            name: 任务名称（如 'morning', 'noon', 'evening'）
            schedule_time: 执行时间（HH:MM 格式）
            task_func: 任务函数
            enabled: 是否启用
            run_immediately: 是否立即执行一次
        """
        task = ScheduledTask(
            name=name,
            schedule_time=schedule_time,
            task_func=task_func,
            enabled=enabled,
            run_immediately=run_immediately,
        )
        self._tasks[name] = task
        logger.info(f"已注册任务 [{name}]，执行时间: {schedule_time}，启用: {enabled}")
    
    def setup_from_config(self, config: Any) -> None:
        """
        从配置对象设置调度任务
        
        Args:
            config: 配置对象，包含各模块的启用状态和时间设置
        """
        morning_enabled = getattr(config, 'morning_review_enabled', True)
        noon_enabled = getattr(config, 'noon_monitor_enabled', True)
        evening_enabled = getattr(config, 'evening_monitor_enabled', True)
        
        morning_time = getattr(config, 'morning_review_time', self.DEFAULT_SCHEDULES['morning'])
        noon_time = getattr(config, 'noon_monitor_time', self.DEFAULT_SCHEDULES['noon'])
        evening_time = getattr(config, 'evening_monitor_time', self.DEFAULT_SCHEDULES['evening'])
        
        run_immediately = getattr(config, 'schedule_run_immediately', False)
        
        if morning_enabled:
            self.register_task(
                name='morning',
                schedule_time=morning_time,
                task_func=self._create_task_wrapper('morning'),
                enabled=True,
                run_immediately=run_immediately,
            )
        
        if noon_enabled:
            self.register_task(
                name='noon',
                schedule_time=noon_time,
                task_func=self._create_task_wrapper('noon'),
                enabled=True,
                run_immediately=run_immediately,
            )
        
        if evening_enabled:
            self.register_task(
                name='evening',
                schedule_time=evening_time,
                task_func=self._create_task_wrapper('evening'),
                enabled=True,
                run_immediately=run_immediately,
            )
    
    def _create_task_wrapper(self, task_name: str) -> Callable:
        """创建任务包装函数"""
        def wrapper():
            task = self._tasks.get(task_name)
            if task and task.enabled:
                self._execute_task(task)
        return wrapper
    
    def _execute_task(self, task: ScheduledTask) -> None:
        """安全执行任务"""
        try:
            logger.info("=" * 50)
            logger.info(f"任务 [{task.name}] 开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 50)
            
            task.task_func()
            
            task.last_run = datetime.now()
            task.last_status = 'success'
            logger.info(f"任务 [{task.name}] 执行完成 - {task.last_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            task.last_status = 'failed'
            logger.exception(f"任务 [{task.name}] 执行失败: {e}")
    
    def _setup_schedule_jobs(self) -> None:
        """设置所有任务的定时调度"""
        for name, task in self._tasks.items():
            if task.enabled:
                self.schedule.every().day.at(task.schedule_time).do(
                    self._execute_task, task
                )
                logger.info(f"已设置定时任务 [{name}]，执行时间: {task.schedule_time}")
    
    def _run_immediate_tasks(self) -> None:
        """立即执行标记的任务"""
        for name, task in self._tasks.items():
            if task.enabled and task.run_immediately:
                logger.info(f"立即执行任务 [{name}]...")
                self._execute_task(task)
    
    def run(self) -> None:
        """
        运行调度器主循环
        
        阻塞运行，直到收到退出信号
        """
        self._running = True
        
        self._setup_schedule_jobs()
        self._run_immediate_tasks()
        
        logger.info("调度管理器开始运行...")
        self._log_next_runs()
        
        while self._running and not self.shutdown_handler.should_shutdown:
            self.schedule.run_pending()
            time.sleep(30)
            
            if datetime.now().minute == 0 and datetime.now().second < 30:
                self._log_next_runs()
        
        logger.info("调度管理器已停止")
    
    def _log_next_runs(self) -> None:
        """打印下次执行时间"""
        jobs = self.schedule.get_jobs()
        if jobs:
            next_runs = []
            for job in jobs:
                if job.next_run:
                    next_runs.append(f"{job.next_run.strftime('%H:%M:%S')}")
            if next_runs:
                logger.info(f"调度器运行中... 下次执行时间: {', '.join(next_runs)}")
    
    def stop(self) -> None:
        """停止调度器"""
        self._running = False
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._tasks.get(name)
        if task:
            return {
                'name': task.name,
                'schedule_time': task.schedule_time,
                'enabled': task.enabled,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'last_status': task.last_status,
            }
        return None
    
    def get_all_tasks_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务状态"""
        return {name: self.get_task_status(name) for name in self._tasks}


def create_scheduler_manager(
    morning_func: Optional[Callable] = None,
    noon_func: Optional[Callable] = None,
    evening_func: Optional[Callable] = None,
    config: Optional[Any] = None,
) -> SchedulerManager:
    """
    便捷函数：创建并配置调度管理器
    
    Args:
        morning_func: 晨间复盘任务函数
        noon_func: 午间监测任务函数
        evening_func: 晚间监测任务函数
        config: 配置对象
    
    Returns:
        配置好的调度管理器
    """
    manager = SchedulerManager()
    
    if morning_func:
        manager.register_task(
            name='morning',
            schedule_time=getattr(config, 'morning_review_time', '07:00') if config else '07:00',
            task_func=morning_func,
            enabled=getattr(config, 'morning_review_enabled', True) if config else True,
        )
    
    if noon_func:
        manager.register_task(
            name='noon',
            schedule_time=getattr(config, 'noon_monitor_time', '12:00') if config else '12:00',
            task_func=noon_func,
            enabled=getattr(config, 'noon_monitor_enabled', True) if config else True,
        )
    
    if evening_func:
        manager.register_task(
            name='evening',
            schedule_time=getattr(config, 'evening_monitor_time', '19:00') if config else '19:00',
            task_func=evening_func,
            enabled=getattr(config, 'evening_monitor_enabled', True) if config else True,
        )
    
    return manager


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    def morning_task():
        print(f"晨间复盘任务执行... {datetime.now()}")
    
    def noon_task():
        print(f"午间监测任务执行... {datetime.now()}")
    
    def evening_task():
        print(f"晚间监测任务执行... {datetime.now()}")
    
    manager = create_scheduler_manager(
        morning_func=morning_task,
        noon_func=noon_task,
        evening_func=evening_task,
    )
    
    print("启动测试调度管理器（按 Ctrl+C 退出）")
    manager.run()
