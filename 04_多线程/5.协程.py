"""
时间：2025/8/3  14:23
"""

import time
import asyncio


#
#
# def func():
#     print('我爱黎明')
#     time.sleep(1)
#     print('我真的爱黎明')
#
#
# if __name__ == '__main__':
#     func()

# input()程序也是处于阻塞状态
# requests.get(bilibili)在网络请求返回数据之前，程序也是处于阻塞状态的
# 一般情况下，当程序处于 I0操作的时候，线程都会处于阻塞状态

# 协程:当程序遇见了I0操作的时候，可以选择性的切换到其他任务上
# 在微观上是一个任务一个任务的进行切换。切换条件一般就是I0操作
# 在宏观上，我们能看到的其实是多个任务一起在执行
# 多任务异步操作

# 上方所讲的一切。都是在单线程的条件下，通过协程的切换，实现多任务异步操作。

# python编写协程的程序


# async def func():  # 定义协程，使用async关键字
#     print('你好，我是协程')
#
#
# if __name__ == '__main__':
#     g = func()  # 此时的函数是异步协程函数，此时函数执行得到的是一个协程对象，并没有执行协程函数的过程。
#     print(g)
#     asyncio.run(g)  # 执行协程函数，此时协程函数才开始执行。

# async def func1():
#     print('你好我是协程1')
#     await asyncio.sleep(1)  # 如果是time.sleep(1)，则此时程序会阻塞，冻结整个事件循环。事件循环无法做任何其他事。
#     print('你好，我是协程1')  # 如果是await asyncio.sleep(1)，暂停当前协程，并将控制权交还给事件循环。
#
#
# async def func2():
#     print('你好我是协程2')
#     await asyncio.sleep(2)
#     print('你好，我是协程2')
#
#
# async def func3():
#     print('你好我是协程3')
#     await asyncio.sleep(3)
#     print('你好，我是协程3')
#
#
# async def func4():
#     print('你好我是协程4')
#     await asyncio.sleep(4)
#     print('你好，我是协程4')
#
#
# # 1. 创建一个异步的 main 函数来包裹我们的异步逻辑
# async def main():
#     f1 = func1()
#     f2 = func2()
#     f3 = func3()
#     f4 = func4()
#     tasks = [f1, f2, f3, f4]
#
#     # 2. 在这里使用 await 是合法的，因为我们在 async 函数内部
#     t1 = time.time()
#     await asyncio.gather(*tasks)  # 直接 await，不需要获取 loop
#     t2 = time.time()
#     print(t2 - t1, '秒')
#
#
# # 3. 使用 asyncio.run() 来启动整个异步程序
# if __name__ == '__main__':
#     asyncio.run(main())

# 在爬虫领域的应用
async def download(url):
    print('准备下载')
    await asyncio.sleep(2)  # 网络请求
    print('下载完成')


async def main():
    urls = ['https://www.bilibili.com', 'https://www.163.com', 'https://www.baidu.com']

    tasks = []
    for url in urls:
        d = download(url)
        tasks.append(d)
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
