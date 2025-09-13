"""
时间：2025/7/19  10:08
"""

# 线程池和进程池
# 线程池：一次性开辟一些线程，将任务分发给线程，线程执行完后再回收线程，适合短任务。
# 进程池：创建进程，将任务分发给进程，进程执行完后再回收进程，适合长任务。
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def fn(name):
    for i in range(2025):
        print(name, i)


if __name__ == '__main__':
    # 线程池
    with ThreadPoolExecutor(50) as t:  # 最大线程数为50
        for i in range(100):  # 任务数为10
            t.submit(fn, name=f'线程{i}')  # 提交任务
    # 等待所有线程执行完毕
    print('线程池执行完毕')
