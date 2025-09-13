"""
时间：2025/7/18  17:31
"""

from multiprocessing import Process
import time


# 进程跟线程的区别：
# 进程是操作系统分配资源的最小单位，线程是CPU调度的最小单位。
# Thread与Process的区别：
# 1. 调度方式：Thread是用户态的，Process是内核态的，因此Thread比Process更轻量级，切换速度快。
# 2. 系统开销：创建和撤销进程比创建和撤销线程更加复杂，系统开销也更大。
# 3. 通信方面：Thread之间可以直接读写数据，而Process需要通过IPC（Inter-Process Communication，进程间通信）来交换数据。
# 4. 资源共享：Thread之间共享内存，Process之间共享内存不太可能。
# 5. 启动方式：Thread是由主线程来启动和管理的，而Process是由操作系统来启动和管理的。
# 6. 系统资源：Thread比Process更占用系统资源，因为每个Thread都需要一个栈和寄存器等资源。
# 7. 并发性：Thread可以并发执行，而Process只能顺序执行。
# 8. 系统限制：Thread的数量受限于操作系统的线程限制，而Process的数量没有限制。

def func(name):
    for i in range(3000):
        time.sleep(1)  # 模拟耗时操作
        print(f'{name} 执行: {i}')


if __name__ == '__main__':
    p = Process(target=func, args=('子进程',))  # args参数为传递给子进程的参数
    p.start()

    func('主进程')  # 主进程也执行相同函数

