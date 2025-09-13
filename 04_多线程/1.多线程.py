"""
时间：2025/7/18  16:49
"""

# 线程，进程
# 进程是资源单位，每一个进程至少要有一个线程，线程是CPU调度的最小单位，一个进程可以有多个线程，一个线程只能属于一个进程。
# 线程是执行单位，它是进程的一个执行流，一个进程可以包含多个线程，线程间共享进程的内存空间。

# 启动每一个程序默认都会有一个主线程

# def func():
#     for i in range(1000):
#         print('func', i)
#
#
# if __name__ == '__main__':
#     func()
#     for i in range(1000):
#         print('main', i)

# 多线程
from threading import Thread


# def func():
#     for i in range(1000):
#         print('func', i)
#
#
# if __name__ == '__main__':
#     t = Thread(target=func)  # 创建线程对象
#     t.start()  # 启动线程,多线程状态下，主线程和子线程并发执行
#     for i in range(1000):  # 主线程执行完毕后，才会执行
#         print('main', i)

class MyThread(Thread):
    def run(self):  # 固定的  ->当线程被执行的时候，就会调用run方法
        for i in range(1000):
            print('子线程', i)


if __name__ == '__main__':
    t = MyThread()  # 创建线程对象
    t.start()  # start可以自动调用run方法
    # t.run()  # 也可以手动调用run方法，效果一样
    for i in range(1000):
        print('主线程', i)
